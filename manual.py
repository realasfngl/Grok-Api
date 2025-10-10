from core import Log, Grok


Log.Info(Grok("PROXYHERE (http://user:pass@ip:port)").start_convo("hey how are you today"))