## Configuration

SensuTop looks in /etc/sensutop.json first, then ~/.sensutop.json, and 
lastly defaults to localhost. The configuration file looks like this:

```
{
    "api_endpoints": {
        "system1": {
            "host": "system1.com",
            "password": "blapassword",
            "port": 443,
            "ssl": true,
            "username": "blauser"
        },
        "system2": {
            "host": "system2.com",
            "password": "blapassword",
            "port": 443,
            "ssl": true,
            "username": "blauser"
        },
        "localhost": {
            "host": "localhost",
            "port": 4567,
        }
    }
}
```
