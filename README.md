# check_pmg

## About
This plugin checks and warns for anomalies regarding users exceeding an overall sent mail count, spam mail count or virus mail count of proxmox mail gateway. It uses the `pmgsh` API to retrieve the data and has to be run locally on your PMG instance.

The plugin can also check your configuration for configured relay host domains, as those get sometimes overwritten in update processes.

## Install
Add the following entry to `visudo` (adapt to user this script is invoked with):
```
nagios ALL=NOPASSWD: /usr/bin/pmgsh get *
```

## Usage
```
usage: check_pmg.py [-h] [-c MAXCOUNT] [-v VIRUSCOUNT] [-s SPAMCOUNT] [-d DOMAIN]

Check Proxmox status

options:
  -h, --help            show this help message and exit
  -c MAXCOUNT, --maxcount MAXCOUNT
                        Threshold for max. mails sent in a day. Default: 1000
  -v VIRUSCOUNT, --viruscount VIRUSCOUNT
                        Threshold for max. spam mails sent in a day. Default: 5
  -s SPAMCOUNT, --spamcount SPAMCOUNT
                        Threshold for max. virus mails sent in a day. Default: 10
  -d DOMAIN, --domain DOMAIN
                        Specify a domain which will be validated as configured relay host. Default: None
```
Example: `python3 check_pmg.py -c 3000 -d domain1.com -d mail.domain2.com`

