import paramiko as pm
import logging
import os
import re
import time
from dotenv import load_dotenv
from wakeonlan import send_magic_packet
from mcrcon import MCRcon
from rcon_client import rcon_client

log = logging.getLogger()

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class shell(object):
    
    def __new__(self):
        if not hasattr(self, 'instance'):
            self.instance = super(shell, self).__new__(self)
            load_dotenv()
            self.SERVER_PC_MAC = os.getenv('SERVER_MAC')
            self.SERVER_IP = os.getenv('SERVER_IP')
            self.current_game_type = None
            self.connection = None
            self.stdIn = None
            self.stdOut = None
            self.stdErr = None
        return self.instance

    def establish_connection(self, command_user):
        # If the server is not online, turn it on
        if not self.ping_server():
            self.wake_remote_server()
        self.connection = pm.client.SSHClient()
        self.connection.set_missing_host_key_policy(pm.client.WarningPolicy())
        log.info('Establishing connection to remote')
        if command_user == 'mc_user':
            username = os.getenv('MC_USER')
            password = os.getenv('MC_USER_PASSWORD')
        elif command_user == 'steam':
            username = os.getenv('STEAM_USER')
            password = os.getenv('STEAM_USER_PASSWORD')
        else:
            assert 'Invalid user passed, cannot continue'
        self.connection.connect(self.SERVER_IP, username=username, password=password)
        stdin, stdout, stderr = self.connection.exec_command('whoami')
        log.info(f'Logged into remote ({self.SERVER_IP}) as {{{stdout.read().decode().strip()}}}')

    def wake_remote_server(self):
        log.info(f'sending wake-up packet to: {self.SERVER_PC_MAC}')
        send_magic_packet(self.SERVER_PC_MAC)
        MAX_ATTEMPTS = 15
        for i in range(MAX_ATTEMPTS,0,-1):
            send_magic_packet(self.SERVER_PC_MAC)
            log.info(f'Waiting {i} for remote server to come online')
            if self.ping_server():
                break
        time.sleep(1)

    def sleep_server(self):
        self.connection = None
        log.info('Sending suspend command to remote')
        stdin, stdout, stderr = self.exec_command('mc_user', 'sudo -S pm-suspend')
        stdin.write(os.getenv('MC_USER_PASSWORD') + '\n')
        stdin.flush()
        self.connection = None
        log.info('Remote suspended')
  
    def start_server(self, game_type):
        if game_type == 'minecraft':
            self.current_game_type = 'minecraft'
            self.start_minecraft_process()
        elif game_type == 'palworld':
            self.current_game_type = 'palworld'
            self.start_palworld_process()

    def stop_server(self):
        if self.current_game_type == 'minecraft':
            self.stop_minecraft_process()
        elif self.current_game_type == 'palworld':
            self.stop_palworld_process()
    
    def start_minecraft_process(self):
        self.stdIn, self.stdOut, self.stdErr = self.exec_command('mc_user', 'cd paper && java -Xms2G -Xmx15G -jar paper-server.jar --nogui', get_pty=True)         

    def start_palworld_process(self):
        self.stdIn, self.stdOut, self.stdErr = self.exec_command('steam', 'cd Steam/steamapps/common/PalServer &&./PalServer.sh -useperfthreads -NoAsyncLoadingThread -UseMultithreadForDS', get_pty=True)

    def list(self):
        try:
            with MCRcon(self.SERVER_IP, os.getenv('MC_RCON_PASSWORD')) as mcr:
                return mcr.command('list')
        except ConnectionRefusedError:
            return 'Server is offline'

    def stop_minecraft_process(self):
        log.info('Sleeping minecraft server')
        with MCRcon(self.SERVER_IP, os.getenv('MC_RCON_PASSWORD')) as mcr:
            mcr.command('stop')
        while not self.stdOut.channel.exit_status_ready():
            log.info('Waiting for server to shutdown fully')
            time.sleep(5)
        self.sleep_server()

    def stop_palworld_process(self):
        log.info('Sleeping palworld server')
        rcon_client().save()
        rcon_client().shutdown(10, 'server_shutdown_10_seconds!')
        time.sleep(11)
        while not self.stdOut.channel.exit_status_ready():
            log.info('Waiting for server to shutdown fully')
            time.sleep(5)
        self.sleep_server()

    def exec_command(self, command_user, *args, **kwargs):
        if self.connection is None:
            log.info("No connection, establishing")
            self.establish_connection(command_user)
        else:
            log.info("Connection exists, issuing command")
        return self.connection.exec_command(*args, **kwargs)
        
    def is_server_online(self):
        for x in range(9):
            if self.ping_server():
                return True
            time.sleep(1)
        return False
    
    def ping_server(self):
        return os.system(f"ping -c 1 {self.SERVER_IP} > /dev/null") == 0

    def clean_line(self):
        return ansi_escape.sub('', self.stdOut.readline())

