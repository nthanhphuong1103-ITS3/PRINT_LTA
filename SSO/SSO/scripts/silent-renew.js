//var configSSO = {
//	authority: 'https://auth.ltacv.com',
//	client_id: 'cms',
//	redirect_uri: window.location.origin + '/Content/SSO/html/auth.html',
//	post_logout_redirect_uri: window.location.origin + '/Content/SSO/html/silent-renew.html',
//	response_type: "code",
//	scope: "openid profile email",
//};
//var mgr = new Oidc.UserManager(configSSO);
var mgr = new Oidc.UserManager();
mgr.signinSilentCallback()
	.then(function (user) {
   window.location = "/";
})
    .catch(function (er) {
       window.location = "/";
    });
