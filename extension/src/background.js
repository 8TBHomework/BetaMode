import sha256 from "crypto-js/sha256";

const NATIVE_HOST_NAME = "io.github.8tbhomework.betamode";

let idTabMap = {};
let nativeHostPort = browser.runtime.connectNative(NATIVE_HOST_NAME);

function enqueueImage(imgId, imgUrl) {
    nativeHostPort.postMessage({type: 0, id: imgId, url: imgUrl});
    console.debug(`Queued request for image with id ${imgId}.`);
}

function dequeueImage(imgId) {  // Tell host to dequeue the image
    nativeHostPort.postMessage({type: 1, id: imgId});
    console.debug(`Dequeued request for image with id ${imgId}.`);
}

function removeTabFromMap(imgId, tabId) {
    idTabMap[imgId] = idTabMap[imgId].filter(item => item !== tabId);

    if (idTabMap[imgId].length === 0)  // if no tab wants this image anymore, remove it
        delete idTabMap[imgId];
}

browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
    const tabId = sender.tab.id;
    if (request.type === "enqueue") {
        const imgUrl = request.url;
        const imgId = sha256(imgUrl).toString();
        if (!(imgId in idTabMap))
            idTabMap[imgId] = [];  // create list if it doesn't exist

        if (!idTabMap[imgId].includes(tabId)) {  // If tab has image more than once
            idTabMap[imgId].push(tabId);

            enqueueImage(imgId, imgUrl);
        }
        sendResponse({type: "queued", id: imgId});  // Always satisfy content.js
    } else if (request.type === "dequeue") {
        const imgId = request.id;
        removeTabFromMap(imgId, tabId);
        if (!(imgId in idTabMap)) // no tab wants this anymore
            dequeueImage(imgId, true);
    }
});

nativeHostPort.onMessage.addListener(msg => {
    console.debug(`Message from native host with type ${msg.type}`);
    if (msg.type === "debug") {
        console.debug(msg.debug);
    } else if (msg.type === "status") {
        console.log(`Host queue size: ${msg.queue}, Our queue size: ${Object.keys(idTabMap).length}, Worker alive: ${msg.worker}`);
    } else if (msg.type === "result") {
        let imgId = msg.id;

        console.debug(`Received result from native host: ${msg.data !== null} with id ${imgId}`);

        if (msg.data !== null) {
            idTabMap[imgId].forEach((tabId) => {
                console.debug(`Found tab ${tabId} for id ${imgId}`);
                browser.tabs.sendMessage(tabId, {type: "done", id: imgId, src: msg.data});
                removeTabFromMap(imgId, tabId);
            });
        }
    }
});

browser.tabs.onRemoved.addListener(closedTabId => {
    Object.keys(idTabMap).forEach(imgId => {
        removeTabFromMap(imgId, closedTabId);
        if (!(imgId in idTabMap)) // no tab wants this anymore
            dequeueImage(imgId, true);

    });
});

setInterval(() => {
    nativeHostPort.postMessage({type: 2});
}, 5000);
