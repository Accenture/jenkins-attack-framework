import jenkins.security.*

User u = User.get("@{user}")  
t = u.getProperty(ApiTokenProperty.class).getTokenStore()
t.revokeToken("@{token}")
println "Success"