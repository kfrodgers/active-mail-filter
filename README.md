# Active Mail Filtering

A python module for filtering email. Filters mail from a source folder, typically inbox, to a target folder. The filter first creates a collection of From address already in the target folder. Then for each address it matches item from the same address in the source folder and moves those to the target folder.

## Installation
This package require a redis server, the location (IP address) of the server, default 127.0.0.1, is stored in the configuration file. 

Install active_mail_filter
```bash
git clone https://github.com/krodgers/active_mail_filter.git
sudo pip install ./active_mail_filter
```

### Configuration File (amf_update_conf)
The amf_update_conf command can be used to create a default configuration file (/usr/local/etc/amf.conf). You should edit this file and change the cipher_key, admin password and any other parameters needed to fit your environment.

```bash
Usage: amf_update_conf [-v] [-i <http-client-address> ] [-u <http-user>:<http-password>]
                       [-r <redis-server>] [-k <redis-key>] [-l <log-level>] [-c <cipher-key>]
```

## Raspberry Pi Install
```bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install python-pip
sudo apt-get install python-dev
sudo apt-get install redis-server
sudo pip install -U pip
sudo pip install ./active_mail_filter
sudo cp ./active_mail_filter/conf/amf_daemon /etc/init.d/
sudo chmod +x /etc/init.d/amf_daemon
```

To start the daemon simply enter...

```bash
sudo update-rc.d amf_daemon defaults
sudo service amf_daemon start
```

To stop amf_daemon run...

```bash
sudo service amf_daemon stop
```

## Mac OSX Install
```bash
sudo pip install ./active_mail_filter
sudo cp ./active_mail_filter/conf/org.mail.filter.amf-daemon.plist /System/Library/LaunchDaemons/
```

To start the daemon simply enter...

```bash
sudo launchctl load -w /System/Library/LaunchDaemons/org.mail.filter.amf-daemon.plist
```

To stop amf_daemon run...

```bash
sudo launchctl unload  /System/Library/LaunchDaemons/org.mail.filter.amf-daemon.plist
```

## Linux Systemd Install
```bash
sudo pip install ./active_mail_filter
sudo cp ./active_mail_filter/conf/amf_daemon.service /usr/lib/systemd/system/
```

To start the daemon simply enter...

```bash
sudo systemctl enable amf_daemon
sudo systemctl start amf_daemon
```

To stop amf_daemon run...

```bash
sudo systemctl stop amf_daemon
```

## Commands

amf_add_rule     - Add a new filter rule <br />
amf_daemon       - The mail filtering daemon, must be run as root <br />
amf_del_rule     - Deletes a filter rule <br />
amf_list_rules   - Lists filter rules <br />
amf_mod_rule     - Modifies a filter rule <br />
amf_start_daemon - Start filtering mail <br />
amf_stop_daemon  - Stop filtering mail <br />
amf_update_conf  - Create or update the configuration file <br />

## Environment Variables

AMF_CONF_FILE - Configuration file location <br />
AMF_REDIS_SERVER - IP address or hostname of redis server <br />
AMF_HTTP_SERVER - IP address or hostname of RESTful API server <br />
AMF_HTTP_PORT - Port of RESTful API server <br />

## RESTful API

The API requires basic authentication, the username and password are stored in the configuration file.

#### GET
http://127.0.0.1:5000/ - Get running threads <br />
http://127.0.0.1:5000/list - Get list of filter rule UUIDs <br />
http://127.0.0.1:5000/show/string:UUID - Get filter rule details by UUID <br />
http://127.0.0.1:5000/folders/string:UUID - List mail folders for user in rule with specified UUID <br />
http://127.0.0.1:5000/ - List running threads <br />

#### PUT
http://127.0.0.1:5000/add - Add a new filter rule <br />
*Parameter are 'user=', 'password=', 'email=', 'mail_server=', 'source=' and 'target='* <br />
http://127.0.0.1:5000/update/string:UUID - Update an existing filter rule <br />
*Same parameters as above but only specify parameters that need to be updated* <br />

#### DELETE
http://127.0.0.1:5000/show/string:UUID - Delete rule by UUID <br />

#### POST
http://127.0.0.1:5000/start - Start processing filter rules <br />
http://127.0.0.1:5000/stop - Stop processing filter rules <br />
http://127.0.0.1:5000/folders - Get list of folders for user <br />
*Parameters are 'user=', 'password=' and 'mail_server='* <br />

### Todo's
1. Add SSL support to RESTful API and have it controlled by a configuration file option, default on
2. Create GUI interface
3. Improve/add comments
4. Add thread to look for unseen (new) messages in folder with shorter loop time than full folder scan

### Contribution

Create a fork of the project into your own repository. Make all your necessary changes and create a pull request with a description on what was added or removed and details explaining the changes in lines of code. If approved, project owners will merge it.

### Licensing

Copyright (c) [2016], [Kevin Rodgers]
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

### Support

Please file bugs and issues at the Github issues page.
