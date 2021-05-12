async function main() {
    console.log(firebase.auth().currentUser.email);
    $('#username').text(firebase.auth().currentUser.email);
    loadAnnotators();
    loadJobs();
    submitBtn = document.querySelector('#submit');
    submitBtn.disabled=null;
    submitBtn.addEventListener('click',()=>{submit()})
};

const jobs = {};

async function loadAnnotators () {
    const instanceRef = firebase.firestore()
        .collection('environment')
        .doc('annotators');
    const instance = await instanceRef.get();
    const container = document.querySelector('#annotators');
    while (container.firstChild) container.removeChild(container.firstChild)
    let annotators = instance.data().annotators;
    for (let annotator of annotators) {
        let bsCb = document.createElement('div');
        container.appendChild(bsCb);
        bsCb.classList.add('form-check');
        let cb = document.createElement('input');
        bsCb.appendChild(cb);
        cb.type = 'checkbox';
        let cbid = `${annotator}-cb`;
        cb.id = cbid;
        cb.value = annotator;
        cb.classList.add('annot-cb');
        cb.classList.add('form-check-input')
        let label = document.createElement('label');
        bsCb.appendChild(label);
        label.classList.add('form-check-label');
        label.htmlFor = cbid;
        label.innerText = annotator;
    }
}

function loadJobs () {
    const query = firebase.firestore()
        .collection('jobs')
        .where('submitter','==',firebase.auth().currentUser.uid)
        .orderBy('initTime','asc');
    query.onSnapshot(snapshot=>{snapshot.docChanges().forEach(change=>{
        let jobId = change.doc.id;
        let job = change.doc.data();
        if (change.type==='removed') {
            removeJob(jobId);
        } else if (change.type==='modified') {
            modifyJob(jobId, job);
        } else {
            addJob(jobId, job);
        }
    })})
}

function addJob(jobId, job) {
    jobs[jobId] = job;
    let tbody = $('#jobstable tbody');
    let tr = $(document.createElement('tr'));
    fillJobRow(tr, jobId, job);
    tbody.prepend(tr);
}

function fillJobRow(tr, jobId, job) {
    tr.attr('jobid',jobId)
    // Init Time
    let initTime = job.initTime;
    let ts = initTime ? initTime.toDate().toLocaleString() : '';
    tr.append($(document.createElement('td'))
        .text(ts)
    )
    // Status
    tr.append($(document.createElement('td'))
        .text(job.status.display)
    )
    // Output
    let outputTd = $(document.createElement('td'))
    if (job.status.code >= 40) {
        let resultsBtn = $(document.createElement('button'))
            .text('Results')
            .addClass('btn')
            .addClass('btn-outline-dark')
            .addClass('job-results-btn')
            .click(showDownloadPopover);
        outputTd.append(resultsBtn);
    } else {
        outputTd.text('Not yet');
    }
    tr.append(outputTd);
    // Inputs
    tr.append($(document.createElement('td'))
        .text(job.inputNames.join(','))
    )
    // Annotators
    let annotsText = job.annotators.join(', ');
    tr.append($(document.createElement('td'))
        .addClass(['text-truncate'])
        .css('max-width','30ch')
        .text(annotsText)
        .attr('title', annotsText)
    )
    // Genome
    tr.append($(document.createElement('td'))
        .text(job.genome)
    )
    // Job ID
    tr.append($(document.createElement('td'))
        .text(jobId)
    )
    // Delete
    tr.append($(document.createElement('td'))
        .append($(document.createElement('button'))
            .attr('type','button')
            .addClass(['close','btn','btn-sm','btn-outline-danger'])
            .click(deleteJobHandler)
            .append($(document.createElement('span')).text('X').css('hidden','true'))
        )
    )
}

function deleteJobHandler(event) {
    var btn = $(event.target);
    var jobId = btn.parents('tr').attr('jobid');
    firebase.firestore()
        .collection('jobs')
        .doc(jobId)
        .delete();    
}

function removeJob(jobId) {
    $(`tr[jobid=${jobId}]`).remove();
    delete jobs[jobId];
}

function modifyJob(jobId, job) {
    jobs[jobId] = job;
    let tr = $(`tr[jobid=${jobId}]`);
    if (tr) {
        tr.empty();
        fillJobRow(tr, jobId, job);
    }
}

async function submit() {
    let fileInput = document.querySelector('#inputfile');
    let inputs = fileInput.files;
    if (!inputs) return;
    let genome = document.querySelector('#genome').value;
    let annotators = Array.from(document.querySelectorAll('.annot-cb:checked')).map(cb=>cb.value);
    let user = firebase.auth().currentUser;
    let data = {
        inputNames: Array.from(inputs).map(file=>file.name),
        annotators: annotators,
        initTime: firebase.firestore.FieldValue.serverTimestamp(),
        status: {
            code: 0,
            display: 'Uploading',
        },
        genome: genome,
        submitter: user.uid,
    }
    let doc = await firebase.firestore().collection('jobs').add(data);
    let jobId = doc.id;
    let storagePaths = {};
    let storageRoot = firebase.storage().ref();
    for (let input of inputs) {
        let inputRef = storageRoot.child('jobs').child(jobId).child(input.name);
        await inputRef.put(input)
        storagePaths[input.name] = inputRef.fullPath;
    }
    await doc.update({
        inputPaths: storagePaths,
        status: {
            code: 10,
            display: 'Queued',
        },
        submitTime: firebase.firestore.FieldValue.serverTimestamp(),
    })
    return fetch('/submit-job',{
        method:'post',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({jobId:jobId}),
    })
}

function showDownloadPopover(event) {
    const rect = event.target.getBoundingClientRect();
    const jobId = $(event.target).parents('tr').attr('jobid');
    const job = jobs[jobId];
    let dbPath = null;
    let csvPath = null;
    if (job.hasOwnProperty('output') && job.output != null) {
        if (typeof(job.output) === 'object') {
            dbPath = job.output.database ? job.output.database : null;
            csvPath = job.output.csv ? job.output.database : null;
        } else if (typeof(job.output) === 'string') {
            dbPath = job.output;
            csvPath = null;
        }
    }
    const popover = $('#download-popover');
    if (dbPath) {
        popover.find('#database-download')
            .prop('disabled',false)
            .click(()=>{
                firebase.storage().ref().child(job.output.database).getDownloadURL().then((url)=>{
                    downloadURL(url);
                });
            });
    } else {
        popover.find('#database-download').prop('disabled',true);
    }
    if (csvPath) {
        popover.find('#csv-download')
            .prop('disabled',false)
            .click(()=>{
                firebase.storage().ref().child(csvPath).getDownloadURL().then((url)=>{
                    downloadURL(url);
                });
        });
    } else {
        popover.find('#csv-download').prop('disabled',true);
    }
    
    // Keep at bottom
    popover.css('display','block')
        .css('top',`${rect.bottom+5}px`)
        .css('left',`${rect.left}px`);
}

function hideDownloadPopover() {
    $('#download-popover').css('display','none');
}

$(document).on('click',e=>{
    if ($(e.target).closest($('#download-popover')).length === 0 && ! e.target.classList.contains('job-results-btn')) {
        hideDownloadPopover();
    }
})

function downloadURL(url, fileName) {
    const a = document.createElement("a");
    a.href = url;
    a.target = '_blank';
    fileName = fileName ? fileName : url.split("/").pop();
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
}

// Keep at bottom
firebase.auth().onAuthStateChanged(function(user) {
    if (user) {
        main();
    } else {
        window.location.href = '/';
    }
});