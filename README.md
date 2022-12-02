# check_pmg

## About
This plugin checks and warns for anomalies regarding users exceeding an overall sent mail count, spam mail count or virus mail count of proxmox mail gateway. It uses the `pmgsh` API to retrieve the data and has to be run locally on your PMG instance.

As the `sender` statistics endpoint of PMG only counts mails per sender and does not account a single mail with n recipients as n mails, the `detail` endpoint has to be queried for every sender. As this process will take a while, the results need to be cached and updated via a cronjob (see below). Do not attempt do run via icinga / nrpe with the `-dc` as this will result in a timeout.


The plugin can also check your configuration for configured relay host domains, as those get sometimes overwritten in update processes.

## Install
Add the following entry to `visudo` (adapt to user this script is invoked with):
```sh
nagios ALL=NOPASSWD: /usr/bin/pmgsh get *
```

Add an entry to crontab to locally cache the API responses for 30 minutes, i.e.,:
```sh
*/30 * * * * /usr/bin/python3.9 /usr/lib/nagios/plugins/check_pmg.py -dc 1
```

## Usage
```
usage: check_pmg.py [-h] [-c MAXCOUNT] [-v VIRUSCOUNT] [-s SPAMCOUNT] [-d DOMAIN] [-f CACHE_FILE] [-dc DO_CACHING]

Check Proxmox status

optional arguments:
  -h, --help            show this help message and exit
  -c MAXCOUNT, --maxcount MAXCOUNT
                        Threshold for max. mails sent in a day. Default: 500
  -v VIRUSCOUNT, --viruscount VIRUSCOUNT
                        Threshold for max. spam mails sent in a day. Default: 5
  -s SPAMCOUNT, --spamcount SPAMCOUNT
                        Threshold for max. virus mails sent in a day. Default: 10
  -d DOMAIN, --domain DOMAIN
                        Specify a domain which will be validated as configured relay host. Default: None
  -f CACHE_FILE, --cache_file CACHE_FILE
                        Path to the local PMG Caching file.
  -dc DO_CACHING, --do_caching DO_CACHING
                        Run with this flag to create a local caching file.
```
Example: `python3 check_pmg.py -c 3000 -d domain1.com -d mail.domain2.com`

