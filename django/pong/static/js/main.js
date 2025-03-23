document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    // Détection iPad & iPhone
    function isiPad() {
        return navigator.platform.indexOf("iPad") !== -1;
    }

    function isiPhone() {
        return navigator.platform.indexOf("iPhone") !== -1 || navigator.platform.indexOf("iPod") !== -1;
    }

    // Aller à la section suivante
    function gotToNextSection() {
        let el = document.querySelector('.fh5co-learn-more');
        if (el) {
            let w = el.offsetWidth;
            let divide = -w / 2;
            el.style.marginLeft = divide + "px";
        }
    }

    // Disparition du loader
    function loaderPage() {
        let loader = document.querySelector(".fh5co-loader");
        if (loader) {
            loader.style.opacity = 0;
            setTimeout(() => loader.style.display = "none", 500); // Simule fadeOut()
        }
    }

    // FullHeight ajusté selon l'écran
    function fullHeight() {
        if (!isiPad() && !isiPhone()) {
            let elements = document.querySelectorAll(".js-fullheight");
            function updateHeight() {
                elements.forEach(el => el.style.height = (window.innerHeight - 49) + "px");
            }
            updateHeight();
            window.addEventListener("resize", updateHeight);
        }
    }

    // Changer la couleur du bouton menu au scroll
    function toggleBtnColor() {
        let hero = document.getElementById('fh5co-hero');
        let navToggle = document.querySelector('.fh5co-nav-toggle');
        if (hero && navToggle) {
            function onScroll() {
                if (window.scrollY > hero.offsetHeight) {
                    navToggle.classList.add("dark");
                } else {
                    navToggle.classList.remove("dark");
                }
            }
            window.addEventListener("scroll", onScroll);
        }
    }

    // Scroll vers la section suivante
    function ScrollNext() {
        document.body.addEventListener("click", function (event) {
            let link = event.target.closest(".scroll-btn");
            if (!link) return;
            event.preventDefault();
            
            let nextSection = link.closest('[data-next="yes"]')?.nextElementSibling;
            if (nextSection) {
                window.scrollTo({
                    top: nextSection.offsetTop,
                    behavior: "smooth"
                });
            }
        });
    }

    // Click en dehors du menu mobile pour le fermer
    function mobileMenuOutsideClick() {
        document.addEventListener("click", function (event) {
            let menu = document.getElementById("fh5co-offcanvas");
            let toggle = document.querySelector(".js-fh5co-nav-toggle");

            if (menu && toggle && !menu.contains(event.target) && !toggle.contains(event.target)) {
                document.body.classList.remove("offcanvas-visible");
                toggle.classList.remove("active");
            }
        });
    }

    // Affichage du menu offcanvas
    function offcanvasMenu() {
        console.log("offcanvas");
    }

    // Gestion du menu burger
    function burgerMenu() {
        console.log("burgerMenu");
    }

    // Scroll en haut de la page
    function goToTop() {
        let elements = document.querySelectorAll(".js-gotop");
        elements.forEach(el => {
            el.addEventListener("click", function (event) {
                event.preventDefault();
                window.scrollTo({
                    top: 0,
                    behavior: "smooth"
                });
            });
        });
    }

    // Gestion des animations
    function contentWayPoint() {
        let elements = document.querySelectorAll('.animate-box');
        let observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !entry.target.classList.contains("animated")) {
                    entry.target.classList.add("fadeInUp", "animated");
                }
            });
        }, { threshold: 0.95 });

        elements.forEach(el => observer.observe(el));
    }

    // Appeler les fonctions après le chargement
    gotToNextSection();
    loaderPage();
    fullHeight();
    toggleBtnColor();
    ScrollNext();
    mobileMenuOutsideClick();
    offcanvasMenu();
    burgerMenu();
    goToTop();
    contentWayPoint();
});
