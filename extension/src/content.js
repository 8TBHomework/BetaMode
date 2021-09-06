import sha256 from "crypto-js/sha256";

function handleNewIMG(imgElem) {
    const imgUrl = imgElem.src;
    if (imgUrl) {
        const imgId = sha256(imgUrl).toString();
        browser.runtime.sendMessage({type: "enqueue", id: imgId, url: imgUrl});
        imgElem.setAttribute("betamode", imgId);
    } // TODO: handle images with no src
}

browser.runtime.onMessage.addListener(msg => {
        if (msg.type === "done") {
            const elem = document.querySelector(`[betamode="${msg.id}"]`);
            if (elem == null) { // element disappeared
                return;
            }
            elem.addEventListener("load", () => {
                elem.setAttribute("betamode-done", "1");
            });
            elem.src = msg.src;
            elem.removeAttribute("srcset");
        }
    }
);

function queueImages() {
    for (const e of document.querySelectorAll("img:not([betamode])")) {
        handleNewIMG(e);
    }
}

const config = {attributes: true, childList: true, subtree: true};

const observer = new MutationObserver(mutations => {
    mutations.forEach(mutation => {
        if (mutation.type === "childList") {
            mutation.removedNodes.forEach(node => {
                if (node.hasAttribute("betamode") && !node.hasAttribute("betamode-done")) {
                    chrome.runtime.sendMessage({type: "dequeue", id: node.getAttribute("betamode")});
                }
            });
        }
    });
});

observer.observe(document.body, config);

setInterval(queueImages, 500);
queueImages();
