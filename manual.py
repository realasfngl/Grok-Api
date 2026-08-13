from core import Log, Grok

# Optional: pass your sso cookie and/or proxy
# cookie = "sso=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
cookie = None
proxy = None

message1: str = "Hey how are you??"
Log.Info("USER: " + message1)
data1 = Grok(model="grok-3-fast", proxy=proxy, cookie=cookie).start_convo(message1, extra_data=None)
Log.Info("GROK: " + str(data1.get("response", data1)))

if isinstance(data1, dict) and "extra_data" in data1 and data1["extra_data"]:
    message2: str = "Tell me a joke"
    Log.Info("USER: " + message2)
    data2 = Grok(model="grok-3-fast", proxy=proxy, cookie=cookie).start_convo(message2, extra_data=data1["extra_data"])
    Log.Info("GROK: " + str(data2.get("response", data2)))
