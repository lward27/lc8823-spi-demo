# LC8823 via HW SPI demo

- I took https://github.com/tinue/apa102-pi, stripped it of deps, made it a single blob, added some cmd line params.

```bash  
sudo apt-get install -y python3-dev  
sudo pip3 install --upgrade spidev  
```

# Lucas Updates

First: Create a venv - python -m venv venv  
Start virtual Env. - source venv/bin/activate  
install reqs. - pip3 install -r requirements.txt  

To run application on TB2S, navigate to /opt/,  
replace lc8823-spi-demo repo with new repo: git clone https://github.com/lward27/lc8823-spi-demo.git  
To run app - make sure uvicorn is installed.  
from inside the lc8823-spi-demo directory run: uvicorn main:app --port 8086 --reload  
this will start a webserver that runs in "parallel" (event based async) to the goggles driver.  

### DBUS
There is a file called sample_dbus.py that contains an example of how to register an interface that could  
be used as an event listener  
helpful commands:  

dbus-send --session           \  
  --dest=org.freedesktop.DBus \  
  --type=method_call          \  
  --print-reply               \  
  /org/freedesktop/DBus       \  
  org.freedesktop.DBus.ListNames  

Returns a list of all services currently running on the DBUS session  

dbus-send --system --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames  
return system dbus stuff  

busctl list  
just another way to list dbus stuff  