import jenkins.security.*

User u = User.get("@{command}")  
t = u.getProperty(ApiTokenProperty.class)

for(token in t.getTokenList()){
    println "Token Name: " + token.name;
    println "Create Date: " + token.creationDate.toLocaleString();
    println "UUID: " + token.uuid
    println ""
}