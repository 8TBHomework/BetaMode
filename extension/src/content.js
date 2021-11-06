const API_ENDPOINT = "http://localhost:8000/censored";
const BG_IMG_URL_PATTERN = /url\("(.*)"\)/;


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

function handleNewBGIMG(imgElem) {
    console.log(imgElem);
    const bgIMG = getComputedStyle(imgElem).backgroundImage;
    const match = bgIMG.match(BG_IMG_URL_PATTERN);
    const imgUrl = match.length > 1 ? match[1] : null;
    if (imgUrl) {
        imgElem.style.backgroundImage = `url("${API_ENDPOINT}/${base64url(imgUrl)}")`;
        imgElem.setAttribute("betamode", "1");
    }
}

function queueExistingImages() {
    for (const e of document.querySelectorAll("img:not([betamode])")) {
        handleNewIMG(e);
    }
    const images = findBackgroundImagesRecursively(document.body);
    images.forEach(handleNewBGIMG);
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

function findBackgroundImagesRecursively(element) {
    let images = [];
    if (element != null && element.nodeType === 1) {
        if (getComputedStyle(element).backgroundImage !== "none" && !element.hasAttribute("betamode"))
            images.push(element);

        for (const child of element.childNodes) {
            images = images.concat(findBackgroundImagesRecursively(child));
        }
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
