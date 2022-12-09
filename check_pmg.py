import json
import subprocess
import argparse
from pathlib import Path
import datetime

###########################################################################
# Written by Fabian Ihle, fabi@ihlecloud.de                               #
# Created: 07.10.2022                                                     #
# github: https://github.com/n1tr0-5urf3r/check_pmg                       #
#                                                                         #
# Checks the mail, spam, and virus count for anomalies and validates      #
# configured relay hosts of Proxmox Mail Gateway                          #
#                                                                         # 
# ----------------------------------------------------------------------- #
# Changelog:                                                              #
# 071022 Version 1.0 - Initial release                                    #
# 021222 Version 1.1 - Include sent mails with multiple recipients, cache #
# 091222 Version 1.2 - Fix day parameter                                  #
###########################################################################

class CheckPMG(object):

    def __init__(self, sender_limit, spam_limit, virus_limit, domains, cache_file, do_caching) -> None:
        self.pmg_bin = "/usr/bin/pmgsh"
        self.sudo_bin = "/usr/bin/sudo"
        self.cache_file = Path(cache_file)
        self.do_caching = do_caching

        # Limit per day
        self.sender_limit = sender_limit
        self.spam_limit = spam_limit
        self.virus_limit = virus_limit
        self.domains = domains

        self.exit_code = 0
        self.return_string = ""

        
    def run_shell_command(self, command_list: list):
        """
        Runs a shell command. Output is available in  result.stdout or result.stderr
        
        :param command_list: List of absolute path to command with comma separated parameters
        :return result: command result
        """
        try:
            result = subprocess.run(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if "200" not in result.stderr:
                print(f"{result.stderr}\n")
        except FileNotFoundError as e:
            self.return_string += f"Error: Command {command_list} not found. Is it installed and are all paths correct?\n"
            self.exit_code = 3
            self.exit_with_result()
        return result


    def get_sender_stats(self):
        """
        Retrieves sender statistics from the pmg API.
        """
        todays_day = datetime.datetime.now().day
        result = self.run_shell_command([self.sudo_bin, self.pmg_bin, "get", "statistics/sender", "--day", f"{todays_day}"])
        sender_stats = json.loads(result.stdout)

        return sender_stats

    def get_sender_detail_count(self, address: str):
        """
        Retrieves all mails sent by this address.

        :param address: email address of the sender to be queried
        """
        todays_day = datetime.datetime.now().day
        result = self.run_shell_command([self.sudo_bin, self.pmg_bin, "get", "statistics/detail", "--address", address, "--type", "sender", "--day", f"{todays_day}"])
        sender_details = json.loads(result.stdout)
        return len(sender_details)

    def analyze_sender_stats(self):
        """
        Search for spam, virus and overall sending counts of senders exceeding the configured threshold.
        """
        sender_stats = self.get_sender_stats()
        s = ""
        spam = list(filter(lambda l: l['spamcount'] >= self.spam_limit, sender_stats))
        virus = list(filter(lambda l: l['viruscount'] >= self.virus_limit, sender_stats))


        if self.do_caching:
            cache = []
            print("Starting to cache...")
            for l in sender_stats:
                if l['count'] > 1:
                    overall_count = self.get_sender_detail_count(l['sender'])
                    sender = {"sender": l['sender'], "count": overall_count}
                    cache.append(sender)
            if cache:
                # Write cached result into file
                with open(self.cache_file, "w") as cache_file:
                    json.dump(cache, cache_file)

        # Attempt to load local cache file
        try:
            with open(self.cache_file, "r") as cache_file:
                json_object = json.load(cache_file)
                limit = list(filter(lambda l: l['count'] >= self.sender_limit, json_object))
        except FileNotFoundError as e:
            print(e)
            # No caching file present, fall back to sender count only
            print("No cache file found, falling back to sender endpoint only")
            limit = list(filter(lambda l: l['count'] >= self.sender_limit, sender_stats))

        for k in spam:
            s += f"{k['sender']} Spam count: {k['spamcount']}\n"
        for k in virus:
            s += f"{k['sender']} Virus count: {k['viruscount']}\n"
        for k in limit:
            s += f"{k['sender']} Mail count: {k['count']}\n"

        if spam or virus or limit:
            self.exit_code = 2
            self.return_string += f"⚠️ Warning: \n{s}"
        return

    def verify_domain_configured(self):
        """
        Verify if all domains are configured as relay hosts. Useful if config is overwritten and unnoticed.
        """
        result = self.run_shell_command([self.sudo_bin, self.pmg_bin, "get", "config/domains"])
        domains = json.loads(result.stdout)

        found_domains = [d['domain'] for d in domains]
        diff = list(set(self.domains).difference(found_domains))

        if diff: 
            self.exit_code = 2
            self.return_string += f"\n❌ Critical: Domains {diff} not configured as relay hosts!\n"
        else:
            self.return_string += "✔️ All domains configured.\n"
        return

    def exit_with_result(self):
        """
        Exits the script with the previously defined exit code and ouputs the result string.
        """
        if self.exit_code == 0:
            self.return_string = f"All fine :).\n{self.return_string}"
        print(self.return_string)
        exit(self.exit_code)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check Proxmox status")
    parser.add_argument('-c' , '--maxcount', default=500, action='store', type=int, help="Threshold for max. mails sent in a day. Default: 500")
    parser.add_argument('-v' , '--viruscount', default=5, action='store', type=int, help="Threshold for max. spam mails sent in a day. Default: 5")
    parser.add_argument('-s' , '--spamcount', default=10, action='store', type=int, help="Threshold for max. virus mails sent in a day. Default: 10")
    parser.add_argument('-d' , '--domain', default=[], action='append', help="Specify a domain which will be validated as configured relay host. Default: None")
    parser.add_argument('-f' , '--cache_file', default="/var/opt/check_pmg_cache.json", action='store', type=str, help="Path to the local PMG Caching file.")
    parser.add_argument('-dc' , '--do_caching', default=False, action='store', type=bool, help="Run with this flag to create a local caching file.")

    args = parser.parse_args()

    pmg = CheckPMG(args.maxcount, args.spamcount, args.viruscount, args.domain, args.cache_file, args.do_caching)
    pmg.analyze_sender_stats()
    pmg.verify_domain_configured()
    pmg.exit_with_result()
