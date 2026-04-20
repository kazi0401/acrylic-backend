document.addEventListener("DOMContentLoaded", () => {
  const appShell = document.querySelector(".app-shell");
  const sidebar = document.querySelector("#sidebar");
  const sidebarToggles = document.querySelectorAll("[data-sidebar-toggle]");
  const sidebarCloseTargets = document.querySelectorAll("[data-sidebar-close]");
  const disabledNavLinks = document.querySelectorAll('[aria-disabled="true"]');
  const searchForm = document.querySelector("#search-form");
  const searchInput = document.querySelector("#search-input");
  const mobileBreakpoint = window.matchMedia("(max-width: 900px)");
  const storageKey = "acrylic-sidebar-collapsed";

  const syncSidebarState = () => {
    const isMobile = mobileBreakpoint.matches;
    const isCollapsed = appShell?.classList.contains("sidebar-collapsed");
    const isOpen = document.body.classList.contains("sidebar-open");
    const isExpanded = isMobile ? isOpen : !isCollapsed;

    sidebarToggles.forEach((button) => {
      button.setAttribute("aria-expanded", String(isExpanded));
    });
  };

  const setDesktopSidebarState = (shouldCollapse) => {
    if (!appShell) {
      return;
    }

    appShell.classList.toggle("sidebar-collapsed", shouldCollapse);

    try {
      window.localStorage.setItem(storageKey, shouldCollapse ? "true" : "false");
    } catch (error) {
      console.error("Could not save sidebar state.", error);
    }

    syncSidebarState();
  };

  const closeMobileSidebar = () => {
    document.body.classList.remove("sidebar-open");
    syncSidebarState();
  };

  const handleSidebarToggle = () => {
    if (!appShell || !sidebar) {
      return;
    }

    if (mobileBreakpoint.matches) {
      document.body.classList.toggle("sidebar-open");
      syncSidebarState();
      return;
    }

    const shouldCollapse = !appShell.classList.contains("sidebar-collapsed");
    setDesktopSidebarState(shouldCollapse);
  };

  if (appShell && sidebar) {
    try {
      const savedState = window.localStorage.getItem(storageKey);

      if (savedState === "true" && !mobileBreakpoint.matches) {
        appShell.classList.add("sidebar-collapsed");
      }
    } catch (error) {
      console.error("Could not read sidebar state.", error);
    }

    sidebarToggles.forEach((button) => {
      button.addEventListener("click", handleSidebarToggle);
    });

    sidebarCloseTargets.forEach((target) => {
      target.addEventListener("click", closeMobileSidebar);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeMobileSidebar();
      }
    });

    mobileBreakpoint.addEventListener("change", () => {
      if (mobileBreakpoint.matches) {
        appShell.classList.remove("sidebar-collapsed");
      } else {
        closeMobileSidebar();

        try {
          const savedState = window.localStorage.getItem(storageKey) === "true";
          appShell.classList.toggle("sidebar-collapsed", savedState);
        } catch (error) {
          console.error("Could not restore sidebar state.", error);
        }
      }

      syncSidebarState();
    });

    syncSidebarState();
  }

  disabledNavLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
    });
  });

  if (searchForm && searchInput) {
    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();

      const query = searchInput.value.trim();

      if (!query) {
        searchInput.focus();
        return;
      }

      window.alert(`Search started for: ${query}`);
    });
  }
});
