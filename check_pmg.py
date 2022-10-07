import json
import subprocess
import argparse

class CheckPMG(object):

    def __init__(self, sender_limit, spam_limit, virus_limit, domains) -> None:
        self.pmg_bin = "/usr/bin/pmgsh"
        self.sudo_bin = "/usr/bin/sudo"

        # Limit per day
        self.sender_limit = sender_limit
        self.spam_limit = spam_limit
        self.virus_limit = virus_limit
        self.domains = domains

        self.exit_code = 0
        self.return_string = ""

        
    def run_shell_command(self, command_list):
        """
        Runs a shell command. Output is available in  result.stdout or result.stderr
        
        :param command_list: List of absolute path to command with comma separated parameters
        :return result: command result
        """
        try:
            result = subprocess.run(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.stderr:
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
        result = self.run_shell_command([self.sudo_bin, self.pmg_bin, "get", "statistics/sender", "-day", "1"])
        sender_stats = json.loads(result.stdout)

        return sender_stats

    def analyze_sender_stats(self):
        """
        Search for spam, virus and overall sending counts of senders exceeding the configured threshold.
        """
        sender_stats = self.get_sender_stats()
        s = ""
        spam = list(filter(lambda l: l['spamcount'] > self.spam_limit, sender_stats))
        virus = list(filter(lambda l: l['viruscount'] > self.virus_limit, sender_stats))
        limit = list(filter(lambda l: l['count'] > self.sender_limit, sender_stats))

        for k in spam:
            s += f" {k['sender']} Spam count: {k['spamcount']}\n"
        for k in virus:
            s += f" {k['sender']} Virus count: {k['viruscount']}\n"
        for k in limit:
            s += f" {k['sender']} Mail count: {k['count']}\n"

        if spam or virus or limit:
            self.exit_code = 1
            self.return_string += f"Warning: \n{s}"
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
            self.return_string += f"\nCritical: Domains {diff} not configured as relay hosts!\n"
        return

    def exit_with_result(self):
        """
        Exits the script with the previously defined exit code and ouputs the result string.
        """
        if self.exit_code == 0:
            self.return_string = "All fine :)."
        print(self.return_string)
        exit(self.exit_code)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check Proxmox status")
    parser.add_argument('-c' , '--maxcount', default=1000, action='store', type=int, help="Threshold for max. mails sent in a day.")
    parser.add_argument('-v' , '--viruscount', default=5, action='store', type=int, help="Threshold for max. spam mails sent in a day.")
    parser.add_argument('-s' , '--spamcount', default=10, action='store', type=int, help="Threshold for max. virus mails sent in a day.")
    parser.add_argument('-d' , '--domain', default=[], action='append', help="Specify a domain which will be validated as configured relay host.")

    args = parser.parse_args()

    pmg = CheckPMG(args.maxcount, args.spamcount, args.viruscount, args.domain)
    pmg.analyze_sender_stats()
    pmg.verify_domain_configured()
    pmg.exit_with_result()
