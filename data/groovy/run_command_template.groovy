def p = "@{command}".execute(); 
def b = new StringBuffer(); 
p.consumeProcessErrorStream(b);
def e = b.toString()
def o = p.text

if(o != "") println o; 
if(e != "") println e;