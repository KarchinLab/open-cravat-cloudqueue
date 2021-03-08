var manifest=null;

async function main() {
  console.log(firebase.auth().currentUser.email);
  $('#username').text(firebase.auth().currentUser.email);
  loadAnnotators();
  loadManifest();
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
    $('#annotatms').val('');    
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

async function loadManifest() {
  const response = await fetch('/manifest');
  manifest = await response.json();
}

function modulePanel(moduleName) {
  if (manifest === null || typeof manifest !== 'object'){
    return;
  } else if (! moduleName in manifest) {
    return;
  }
  const minfo = manifest[moduleName];
  const panel = $('#module-panel');
  $('#module-panel-title').text(minfo.title);
  const detailSection = $('#module-panel-details');
  detailSection.empty();
  detailSection.append($(document.createElement('div'))
    .text(minfo.description)
    .addClass('module-panel-detail-row')
    );
  const detailRow = (header, content) => {
    const div = $(document.createElement('div'))
      .addClass('module-panel-detail-row');
    div.append($(document.createElement('span'))
      .text(header+': ')
      .addClass('module-panel-detail-header')
      );
    div.append($(document.createElement('span'))
      .text(content)
      .addClass('module-panel-detail-content')
      );
    return div;
  }
  detailSection.append(detailRow('Version',minfo['latest_version']));
  detailSection.append(detailRow('Source version',minfo.data_versions[minfo['latest_version']]));
  detailSection.append(detailRow('Website',minfo.developer.website));
  detailSection.append(detailRow('Citation',minfo.developer.citation));
  detailSection.append(detailRow('Size',humanBytes(minfo.size)));

  showMD(moduleName, minfo.latest_version);

  panel.css('display','');
}

function hideModulePanel() {
  $('#module-panel').css('display','none');
}

async function showMD(moduleName, version) {
  const url = new URL('/markdown', window.location.href);
  url.search = new URLSearchParams({'module':moduleName,'version':version}).toString();
  const response = await fetch(url);
  const mdText = await response.text();
  let mdConverter = new showdown.Converter({tables:true,openLinksInNewWindow:true});
  let mdHtmlRaw = mdConverter.makeHtml(mdText);
  mdHtmlRaw = mdHtmlRaw.replace(/http:/g, 'https:');
  var mdElements = $(mdHtmlRaw);
  const storeUrl = new URL('https://store.opencravat.org');
  for (let img of mdElements.children('img')) {
      let curUrl = new URL(img.src);
      img.src = new URL(`/modules/${moduleName}/${version}/${curUrl.pathname.slice(1)}`, storeUrl).toString();
      img.style.display = 'block';
      img.style.margin = 'auto';
      img.style['max-width'] = '100%';
  }
  const description = $('#module-panel-description');
  description.empty();
  description.append(mdElements);
}

function humanBytes (size) {
  size = parseInt(size);
  if (size < 1024) {
      size = size + ' bytes';
  } else {
      size = size / 1024;
      if (size < 1024) {
          size = size.toFixed(0) + ' KB';
      } else {
          size = size / 1024;
          if (size < 1024) {
              size = size.toFixed(0) + ' MB';
          } else {
              size = size / 1024;
              size = size.toFixed(0) + ' GB';
          }
      }
  }
  return size;
}