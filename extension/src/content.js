chrome.runtime.onMessage.addListener(
    function (request, sender, sendResponse) {
        if (request.type === "done") {
            const elem = document.querySelector(`[betamode="${request.id}"]`);
            if (elem == null) { // element disappeared
                return;
            }
            elem.addEventListener("load", () => {
                elem.setAttribute("betamode-done", "1");
            })
            elem.src = request.src;
            elem.removeAttribute("srcset");
        }
    }
);

function queueImages() {
    for (const e of document.querySelectorAll("img:not([betamode])")) {
        if (e.src) {
            chrome.runtime.sendMessage({type: "enqueue", url: e.src}, response => {
                if (response.type === "queued") {
                    e.setAttribute("betamode", response.id);
                }
            });
        }
    }
}

const config = { attributes: true, childList: true, subtree: true };

const observer = new MutationObserver(mutations => {
    mutations.forEach(mutation => {
        if (mutation.type === "childList") {
            mutation.removedNodes.forEach(node => {
                if (node.hasAttribute("betamode") && !node.hasAttribute("betamode-done")) {
                    chrome.runtime.sendMessage({type: "dequeue", id: node.getAttribute("betamode")})
                }
            });
        }
    });
});

observer.observe(document.body, config)

setInterval(queueImages, 1000);
queueImages()
