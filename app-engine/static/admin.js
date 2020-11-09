async function main() {
  console.log(firebase.auth().currentUser.email);
  loadAnnotators();
  loadApprovedUsers();
};

async function loadAnnotators () {
  const instanceRef = firebase.firestore()
      .collection('environment')
      .doc('annotators')
  const instance = await instanceRef.get();
  const container = document.querySelector('#annotators');
  var para = document.createElement('P');
  var t = document.createTextNode(instance.data().annotators);
  para.appendChild(t);
  document.getElementById("annotators").appendChild(para);
}

async function loadApprovedUsers () {
  const instanceRef = firebase.firestore()
      .collection('environment')
      .doc('authorized-users')
  const instance = await instanceRef.get();
  const container = document.querySelector('#authorizedUsers');
  var para = document.createElement('P');
  var t = document.createTextNode(instance.data().authorizedUsers);
  para.appendChild(t);
  document.getElementById("authorizedUsers").appendChild(para);
}

$(()=>{
  $("#createimage").click(()=>{
    var msoutput = ($("#annotatms").val());
    fetch('/show_selected', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({msoutput}),
    })
      .catch((error) => {console.error('Error:', error);
    });
  });
});

firebase.auth().onAuthStateChanged(function(user) {
    if (user) {
        main();
    } else {
        window.location.href = '/'
    }
});