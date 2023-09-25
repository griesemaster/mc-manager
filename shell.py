import paramiko as pm
import logging
import os
import re
import time
from dotenv import load_dotenv
from wakeonlan import send_magic_packet
from mcrcon import MCRcon

log = logging.getLogger()

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class shell(object):
    
    def __new__(self):
        if not hasattr(self, 'instance'):
            self.instance = super(shell, self).__new__(self)
            load_dotenv()
            self.SERVER_PC_MAC = os.getenv('SERVER_MAC')
            self.SERVER_USER = os.getenv('SERVER_USER')
            self.SERVER_PW = os.getenv('SERVER_USER_PASSWORD')
            self.SERVER_IP = os.getenv('SERVER_IP')
            self.RCON_PW = os.getenv('MC_RCON_PASSWORD')
            self.connection = None
            self.mcIn = None
            self.mcOut = None
            self.mcErr = None
        return self.instance

    def establish_connection(self):
        # If the server is not online, turn it on
        if not self.is_server_online():
            self.wake_remote_server()
        self.connection = pm.client.SSHClient()
        self.connection.set_missing_host_key_policy(pm.client.WarningPolicy())
        log.info('Establishing connection to remote')
        self.connection.connect(self.SERVER_IP, username=self.SERVER_USER, password=self.SERVER_PW)
        stdin, stdout, stderr = self.connection.exec_command('whoami')
        log.info(f'Logged into remote ({self.SERVER_IP}) as {{{stdout.read().decode().strip()}}}')

    def wake_remote_server(self):
        log.info(f'sending wake-up packet to: {self.SERVER_PC_MAC}')
        send_magic_packet(self.SERVER_PC_MAC)
        MAX_ATTEMPTS = 15
        for i in range(MAX_ATTEMPTS,0,-1):
            log.info(f'Waiting {i} for remote server to come online')
            if self.is_server_online():
                break
        time.sleep(1)

    def sleep_server(self):
        if self.connection is None:
            log.warn('Attempting to sleep a closed connection, ignoring')
        log.info('Sending suspend command to remote')
        stdin, stdout, stderr = self.exec_command('sudo -S pm-suspend')
        stdin.write(self.SERVER_PW + '\n')
        stdin.flush()
        self.connection = None
        log.info('Remote suspended')
  
    def start_minecraft_process(self):
        self.mcIn, self.mcOut, self.mcErr = self.exec_command('cd paper && java -Xms2G -Xmx15G -jar paper-server.jar --nogui', get_pty=True)              

    def list(self):
        try:
            with MCRcon(self.SERVER_IP, self.RCON_PW) as mcr:
                return mcr.command('list')
        except ConnectionRefusedError:
            return 'Server is offline'

    def stop_minecraft_process(self):
        log.info('Sleeping server')
        with MCRcon(self.SERVER_IP, self.RCON_PW) as mcr:
            mcr.command('stop')
        while not self.mcOut.channel.exit_status_ready():
            log.info('Waiting for server to shutdown fully')
            time.sleep(5)
        self.sleep_server()

    def exec_command(self, *args, **kwargs):
        if self.connection is None:
            self.establish_connection()
        return self.connection.exec_command(*args, **kwargs)
        
    def is_server_online(self):
        return os.system(f"ping -c 1 {self.SERVER_IP} > /dev/null") == 0

    def clean_line(self):
        return ansi_escape.sub('', self.mcOut.readline())

