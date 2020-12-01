window.addEventListener('load', function () {
  document.getElementById('sign-out').onclick = function () {
    firebase.auth().signOut();
  };

  // FirebaseUI config.
  var uiConfig = {
    signInSuccessUrl: '/submit',
    signInOptions: [
      {
        provider: firebase.auth.EmailAuthProvider.PROVIDER_ID,
        requireDisplayName: false
      }
    ]
  };

  firebase.auth().onAuthStateChanged(function (user) {
    if (user) {
      // User is signed in, so display the "sign out" button and login info.
      document.getElementById('sign-out').hidden = false;
      document.getElementById('login-info').hidden = false;
      console.log(`Signed in as ${user.displayName} (${user.email})`);
      user.getIdToken().then(function (token) {
        document.cookie = "token=" + token;
      });
    } else {
      // User is signed out.
      // Initialize the FirebaseUI Widget using Firebase.
      var ui = new firebaseui.auth.AuthUI(firebase.auth());
      // Show the Firebase login button.
      ui.start('#firebaseui-auth-container', uiConfig);
      // Update the login state indicators.
      document.getElementById('sign-out').hidden = true;
      document.getElementById('login-info').hidden = true;
      // Clear the token cookie.
      document.cookie = "token=";
    }
  }, function (error) {
    console.log(error);
    alert('Unable to log in: ' + error)
  });
});
