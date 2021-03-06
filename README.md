statsd-agent
============

Statsd client to monitor CPU, Memory, Disk and Network

Quickstart
============

## Installation (Ubuntu) [see below]
First, download both *statsd-agent.py* and *statsd-agent.conf*. Create a directory `/opt/statsd-agent` and place *statsd-agent.py* in it. Place the Upstart configuration file *statsd-agent.conf* in `/etc/init/`. The statsd-agent.py will automatically start as service on system startup or you can manually start it using the following command:
```
service statsd-agent start
```

## Installation (Other Linux/Mac)
stasd-agent.py is really just a single python file. You can run it directly using python command:
```
python statsd-agent.py
```

### Full install procedure (Linux):
1. `sudo apt-get update`
2. `sudo apt-get install python-dev git`
3. `git clone https://github.com/sdvicorp/statsd-agent.git`
4. `git checkout cfg`
5. `sudo mkdir /opt/statsd-agent`
6. `sudo cp statsd-agent.py /opt/statsd-agent`
7. `sudo cp statsd-agent.cfg /opt/statsd-agent`
8. `sudo cp statsd-agent.conf /etc/init`
9. `sudo nano /opt/statsd-agent/statsd-agent.cfg`
10. Change fields and other options as necessary
11. `sudo pip install psutil statsd`
12. `sudo service statsd-agent start`
13. `cd ~`
14. `rm -rf statsd-agent`


## Installation (Windows)
1. Grab the `statsd-agent-sfx.exe` file. 
2. Run it. 
3. When prompted for the output path, enter `C:\statsd-agent`.
4. Open `cmd.exe`
5. `cd statsd-agent`
6. Edit the `statsd-agent.cfg` file and set the `host=` and `service=` options (at least).
7. Run `statsd-agent.exe install`
8. Open the Windows Services control panel.
9. Change the statsd agent service setting for startup to automatic.
10. Start the service.

## Running/Stopping (Ubuntu)
Use upstart command to run/stop statsd-agent:
```
service statsd-agent start
service statsd-agent stop
service statsd-agent restart
service statsd-agent status
```
More info about Ubuntu Upstart can be found at http://askubuntu.com/questions/19320/how-to-enable-or-disable-services


## Windows Build

1. Install Python2.7 (into the default `C:\Python27` dir)
2. Install psutil 
3. Install statsd
4. Install py2exe
5. Install git
6. In `C:\User\Administrator`:
7. `git clone https://github.com/sdvicorp/statsd-agent.git`
8. `cd statsd-agent`
9. `git checkout cfg`
10. `python setup.py`
11. `iexpress /N statsd-agent.SED`. Will produce `statsd-agent-sfx.exe` in `C:\User\Administrator`

License
============

    The MIT License (MIT)
    
    Copyright (c) 2013 Mohd Rozi
    
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:
    
    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.
    
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    THE SOFTWARE.
