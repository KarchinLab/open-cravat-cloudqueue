window.addEventListener('load', function () {

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
      user.getIdToken().then(function (token) {
        document.cookie = "token=" + token;
        window.location.href = '/submit';
      });
    } else {
      // User is signed out.
      // Initialize the FirebaseUI Widget using Firebase.
      var ui = new firebaseui.auth.AuthUI(firebase.auth());
      // Show the Firebase login button.
      ui.start('#firebaseui-auth-container', uiConfig);
      // Clear the token cookie.
      document.cookie = "token=";
    }
  }, function (error) {
    console.log(error);
    alert('Unable to log in: ' + error)
  });
});
