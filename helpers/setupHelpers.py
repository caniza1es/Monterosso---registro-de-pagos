def readconfig():
    config = {}
    with open("config.txt","r") as f:
        for line in f:
            line = line.strip()
            key,value = line.split("=")
            config[key] = value
    return config