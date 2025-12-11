from core import Log, Grok
from json import dumps

proxy = "http://user:pass@ip:port"

message1: str = "Hey how are you??"
Log.Info("USER: " + message1)
data1 = Grok(proxy).start_convo(message1, extra_data=None)
Log.Info("GROK: " + data1["response"])

message2: str = "cool stuff"
Log.Info("USER: " + message2)
data2 = Grok(proxy).start_convo(message2, extra_data=data1["extra_data"])
Log.Info("GROK: " + data2["response"])

message3: str = "crazy"
Log.Info("USER: " + message3)
data3 = Grok(proxy).start_convo(message3, extra_data=data2["extra_data"])
Log.Info("GROK: " + data3["response"])

message4: str = "Well this is the 4th message in our chat now omg"
Log.Info("USER: " + message4)
data4 = Grok(proxy).start_convo(message4, extra_data=data3["extra_data"])
Log.Info("GROK: " + data4["response"])

message5: str = "And now the 5th omg"
Log.Info("USER: " + message5)
data5 = Grok(proxy).start_convo(message5, extra_data=data4["extra_data"])
Log.Info("GROK: " + data5["response"])