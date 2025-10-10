from core import Log, Grok
from json import dumps


message1: str = "Hey how are you"
Log.Info("USER: " + message1)
data1 = Grok().start_convo(message1, extra_data=None)
Log.Info("GROK: " + data1["response"])
message2: str = "Glad to hear so what are you up to"
Log.Info("USER: " + message2)
data2 = Grok().start_convo(message2, extra_data=data1["extra_data"])
Log.Info("GROK: " + data2["response"])
message3: str = "Uhh just vibing too lol"
Log.Info("USER: " + message3)
data3 = Grok().start_convo(message3, extra_data=data2["extra_data"])
Log.Info("GROK: " + data3["response"])