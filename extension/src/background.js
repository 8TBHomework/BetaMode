const NATIVE_HOST_NAME = "io.github.8tbhomework.betamode";

let idTabMap = {};
let nativeHostPort = browser.runtime.connectNative(NATIVE_HOST_NAME);

function hostEnqueueImage(imgId, imgUrl) {
    nativeHostPort.postMessage({type: 0, id: imgId, url: imgUrl});
    console.debug(`Queued request for image with id ${imgId}.`);
}

function hostDequeueImage(imgId) {  // Tell host to dequeue the image
    nativeHostPort.postMessage({type: 1, id: imgId});
    console.debug(`Dequeued request for image with id ${imgId}.`);
}

function removeTabFromMap(imgId, tabId) {
    idTabMap[imgId] = idTabMap[imgId].filter(item => item !== tabId);

    if (idTabMap[imgId].length === 0)  // if no tab wants this image anymore, remove it
        delete idTabMap[imgId];
}

// Handle messaging between content
browser.runtime.onMessage.addListener((msg, sender) => {
    const tabId = sender.tab.id;
    if (msg.type === "enqueue") {
        const imgUrl = msg.url;
        const imgId = msg.id;
        if (!(imgId in idTabMap))
            idTabMap[imgId] = [];  // create list if it doesn't exist

        if (!idTabMap[imgId].includes(tabId)) {  // Only add image once per tab
            idTabMap[imgId].push(tabId);

            hostEnqueueImage(imgId, imgUrl);
        }
    } else if (msg.type === "dequeue") {
        const imgId = msg.id;
        removeTabFromMap(imgId, tabId);
        if (!(imgId in idTabMap)) // no tab wants this anymore
            hostDequeueImage(imgId, true);
    }
});

// Handle messaging from native-host
nativeHostPort.onMessage.addListener(msg => {
    console.debug(`Message from native host with type ${msg.type}`);
    switch (msg.type) {
    case "debug":
        console.debug(msg.debug);
        break;
    case "status":
        console.log(`Our queue size: ${Object.keys(idTabMap).length}`);
        console.log(`Host fetch: ${msg.fetch.alive ? "alive" : "dead"}, ${msg.fetch.queue}`);
        console.log(`Host censor: ${msg.censor.alive ? "alive" : "dead"}, ${msg.censor.queue}`);
        console.log(msg.failed);
        break;
    case "result":
        let imgId = msg.id;

        console.debug(`Received result from native host: ${msg.data !== null} with id ${imgId}`);

        if (msg.data !== null && imgId in idTabMap) {
            idTabMap[imgId].forEach((tabId) => {
                console.debug(`Found tab ${tabId} for id ${imgId}`);
                browser.tabs.sendMessage(tabId, {type: "done", id: imgId, src: msg.data});
                removeTabFromMap(imgId, tabId);
            });
        }
        break;
    }
});

browser.tabs.onRemoved.addListener(closedTabId => {
    Object.keys(idTabMap).forEach(imgId => {
        removeTabFromMap(imgId, closedTabId);
        if (!(imgId in idTabMap)) // no tab wants this anymore
            hostDequeueImage(imgId, true);

    });
});

setInterval(() => {
    nativeHostPort.postMessage({type: 2});
}, 5000);

nativeHostPort.postMessage({
    type: 3, // Settings
    user_agent: navigator.userAgent
});
