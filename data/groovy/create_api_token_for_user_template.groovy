import jenkins.security.*

User u = User.get("@{user}")  
t = u.getProperty(ApiTokenProperty.class)  
ts = t.getTokenStore()
println ts.generateNewToken("@{token}").plainValue
