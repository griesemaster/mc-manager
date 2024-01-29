from rcon import Console
from dotenv import load_dotenv

import os
import logging

log = logging.getLogger()


# ------------------------------------------------------------------------------
# Fallback - for testing only
def send_command_fallback(command: str):
    log.info("Testing RCON connection")
    config = fetch_config()
    con = Console(
        host=os.getenv('SERVER_IP'),
        password=os.getenv('PALWORLD_RCON_PASSWORD'),
        port=int(os.getenv('PALWORLD_RCON_PORT')),
        timeout=5000
    )
    res = con.command(command)
    con.close()

    log.debug(res)
    return res


# ------------------------------------------------------------------------------
# Synchronous implementation; manually starts and stops a connection with every command
class rcon_client:
    def __init__(self):
        self.GENERIC_ERROR = "Unable to process your request (server did not respond)"
        log.info("Setting up RCON connection")
        load_dotenv()

    def open(self):
        return Console(
                host=os.getenv('SERVER_IP'),
                password=os.getenv('PALWORLD_RCON_PASSWORD'),
                port=int(os.getenv('PALWORLD_RCON_PORT')),
                timeout=5000)

    # Admin Commands:
    def info(self):
        log.debug("Fetching server info")
        console = self.open()
        res = console.command("Info")
        console.close()
        return res if res else self.GENERIC_ERROR

    def save(self):
        log.debug("Saving world")
        console = self.open()
        res = console.command("Save")
        console.close()
        return res if res else self.GENERIC_ERROR
    
    def online(self):
        # Response is of format `name,playerid,steamid`
        log.debug("Fetching online players")
        console = self.open()
        res = console.command("ShowPlayers")
        console.close()

        players = []
        # format output
        if res:
            lines = res.split()[1:]
            buffer = ["## List of connected player names"]
            for line in lines:
                words = line.split(",")
                name = words[0]
                steam_id = words[2]
                players.append((name, steam_id))
                buffer.append(f"- {words[0]} (Steam ID: {words[2]})")
            output = "\n".join(buffer)
        else:
            output = self.GENERIC_ERROR

        return output, players

    def announce(self, message: str):
        log.debug("Broadcasting message to world")
        console = self.open()
        res = console.command(f"Broadcast {message}")
        console.close()
        # TODO: Consider reformatting server's response
        return res if res else self.GENERIC_ERROR

    def kick(self, steam_id: str):
        log.debug("Kicking player from server")
        console = self.open()
        res = console.command(f"KickPlayer {steam_id}")
        console.close()
        return res if res else self.GENERIC_ERROR

    def ban(self, steam_id: str):
        log.debug("Banning player from server")
        console = self.open()
        res = console.command(f"BanPlayer {steam_id}")
        console.close()
        return res if res else self.GENERIC_ERROR

    def shutdown(self, seconds: str, message: str):
        log.debug(f"Schedule server shutdown in {seconds} seconds")
        console = self.open()
        res = console.command(f"Shutdown {seconds} {message}")
        console.close()
        return res if res else self.GENERIC_ERROR

    def force_stop(self):
        log.debug(f"Terminating the server forcefully")
        console = self.open()
        res = console.command(f"DoExit")
        console.close()
        # TODO: Check if this is supposed to give a response (and alter accordingly)
        return res if res else self.GENERIC_ERROR
