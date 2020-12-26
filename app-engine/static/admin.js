async function main() {
  console.log(firebase.auth().currentUser.email);
  $('#username').text(firebase.auth().currentUser.email);
  loadAnnotators();
  loadApprovedUsers();
  loadImageStatus();
};

function loadImageStatus () {
  const instanceRef = firebase.firestore()
      .collection('environment')
      .doc('imageStatus')
      .onSnapshot(function(doc) {
        if (doc.exists) {
          const container = document.querySelector('#imageStatus');
          var para = document.createElement('P');
          var value = document.createTextNode(doc.data().imageStatus);
          while(container.firstChild){
            container.removeChild(container.firstChild);
          }
          para.appendChild(value);
          document.getElementById("imageStatus").appendChild(para);
        } else {
          console.log("That database entry has not been created");
        }
      });
}

function loadAnnotators () {
  const instanceRef = firebase.firestore()
      .collection('environment')
      .doc('annotators')
      .onSnapshot(function(doc) {
        if (doc.exists) {
          const container = document.querySelector('#annotators');
          var lister = document.createElement('ul');
          while(container.firstChild){
            container.removeChild(container.firstChild);
          }
          container.appendChild(lister);
          for (let annotator of doc.data().annotators) {
            let li = document.createElement('li');
            lister.appendChild(li);
            let value = document.createTextNode(annotator);
            li.appendChild(value);
          }
        } else {
          console.log("No annotators configured yet");
        }
      });
}

function loadApprovedUsers () {
  const instanceRef = firebase.firestore()
  .collection('environment')
  .doc('authorized-users')
  .onSnapshot(function(doc) {
    if (doc.exists) {
      const container = document.querySelector('#authorizedUsers');
      const lister = document.createElement('ul');
      while(container.firstChild){
        container.removeChild(container.firstChild);
      }
      let firstUser = true;
      container.appendChild(lister);
      lister.style['list-style-type'] = 'none';
      for (let user of doc.data().authorizedUsers) {
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
          if (firstUser === true) {
            cb.disabled = true;
            firstUser = false
          }
      } 
  }});
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

function deleteUser() {
  var userRef = firebase.firestore().collection('environment').doc('authorized-users');
  $('.user-cb:checked').each(function() {
    userRef.update({
      authorizedUsers: firebase.firestore.FieldValue.arrayRemove(this.value)
    });
  })
}

firebase.auth().onAuthStateChanged(function(user) {
    if (user) {
        main();
    } else {
        window.location.href = '/'
    }
});
