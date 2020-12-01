async function main() {
  console.log(firebase.auth().currentUser.email);
  loadAnnotators();
  loadApprovedUsers();
  loadImageStatus();
};

function loadImageStatus () {
  const instanceRef = firebase.firestore()
      .collection('environment')
      .doc('imageStatus')
  instanceRef.get().then(function(doc) {
    if (doc.exists) {
      const container = document.querySelector('#imageStatus');
      var para = document.createElement('P');
      var value = document.createTextNode(doc.data().imageStatus);
      para.appendChild(value);
      document.getElementById("imageStatus").appendChild(para);
    } else {
      console.log("That has not been created");
    }
  });

}

async function loadAnnotators () {
  const instanceRef = firebase.firestore()
      .collection('environment')
      .doc('annotators')
  const instance = await instanceRef.get();
  const container = document.querySelector('#annotators');
  const lister = document.createElement('ul')
  container.appendChild(lister)
  for (let annotator of instance.data().annotators) {
    let li = document.createElement('li');
    lister.appendChild(li);
    let value = document.createTextNode(annotator);
    li.appendChild(value);
  }
}

async function loadApprovedUsers () {
  const instanceRef = firebase.firestore()
      .collection('environment')
      .doc('authorized-users')
  const instance = await instanceRef.get();
  const container = document.querySelector('#authorizedUsers');
  const lister = document.createElement('ul');
  container.appendChild(lister);
  lister.style['list-style-type'] = 'none';
  for (let user of instance.data().authorizedUsers) {
    let li = document.createElement('li');
    lister.appendChild(li);
    let cb = document.createElement('input')
    li.appendChild(cb)
    cb.type = 'checkbox'
    let cbid = `${user}-cb`;
    cb.value = user;
    cb.classList.add('user-cb');
    cb.id = cbid;
    let label = document.createElement('label');
    li.appendChild(label)
    label.htmlFor = cbid
    label.innerText = user
  }
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

function addNewUser() {
  var newUser = document.getElementById("newUser").value;
  var userRef = firebase.firestore().collection('environment').doc('authorized-users');
  userRef.update({
    authorizedUsers: firebase.firestore.FieldValue.arrayUnion(newUser)
  });
}

firebase.auth().onAuthStateChanged(function(user) {
    if (user) {
        main();
    } else {
        window.location.href = '/'
    }
});