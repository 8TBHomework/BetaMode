const API_ENDPOINT = "http://localhost:8000/censored";

function base64url(plaintext) {
    return btoa(plaintext).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}

function handleNewIMG(imgElem) {
    const imgUrl = imgElem.src;
    if (imgUrl) {
        imgElem.src = `${API_ENDPOINT}/${base64url(imgUrl)}`;
        imgElem.setAttribute("betamode", "1");
        imgElem.removeAttribute("srcset");
    } // TODO: handle images with no src
}


function queueExistingImages() {
    for (const e of document.querySelectorAll("img:not([betamode])")) {
        handleNewIMG(e);
    }
}

function findImagesRecursively(element) {
    let images = [];
    if (element.tagName === "IMG" && !element.hasAttribute("betamode"))
        images.push(element);

    for (const child of element.childNodes) {
        images = images.concat(findImagesRecursively(child));
    }
    return images;
}

const config = {childList: true, subtree: true};

const callback = function (mutationsList, observer) {
    for (const mutation of mutationsList) {
        if (mutation.type === "childList") {
            for (const e of mutation.addedNodes) {
                const images = findImagesRecursively(e);
                images.forEach(handleNewIMG);
            }
        }
    }
};

const observer = new MutationObserver(callback);
observer.observe(document, config);

queueExistingImages();
