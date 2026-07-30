var mgr = new Oidc.UserManager({ response_mode: "query" });
mgr.signinRedirectCallback().then(function (user) {
    debugger
        if (user == null) {
            document.getElementById("waiting").style.display = "none";
            document.getElementById("error").innerText = "No sign-in request pending.";
            window.location = "/";
        }
        else {
            debugger
            window.history.replaceState({},
                window.document.title,
                window.location.origin + window.location.pathname);
            window.location = user.state || "/";
        }
    })
    .catch(function (er) {
        document.getElementById("waiting").style.display = "none";
        document.getElementById("error").innerText = er.message;
    });
