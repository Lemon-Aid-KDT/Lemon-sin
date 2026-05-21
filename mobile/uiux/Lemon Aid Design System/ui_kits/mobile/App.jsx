// App.jsx — Root of the Lemon Aid mobile UI kit click-thru prototype.
//
// We wire a tiny screen-stack state machine onto a single IOSDevice
// frame, so the user can navigate through the realistic flow:
//
//   onboarding → home (dashboard) ⇄ capture ⇄ review ⇄ chat ⇄ consent
//
// `go(name)` is the only navigation primitive; bottom-tab clicks call it.

const { useState, useEffect } = React;

function App() {
  useLucide();
  const [state, setState] = useState({
    consents: { ocr: true, health: true, health_connect: false, learning: false },
    captureStage: "camera",
    captureMode: "single", // 'single' | 'multi'
    captures: [],
    flash: "off", // 'off' | 'on' | 'auto'
    cameraPermission: null, // null | 'granted' | 'denied' — show the system sheet first
    album: "recents",
  });
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [menuOpen, setMenuOpen]       = useState(false);
  // Skip the splash if the URL has #home/#capture/etc — useful for direct
  // links from the design system tab.
  const initial = (window.location.hash || "").replace("#", "") || "onboarding";
  const [route, setRoute] = useState(initial);

  // Listen for external hash changes (used by demo nav buttons + screenshot
  // tooling). This makes deep-linking work end-to-end.
  useEffect(() => {
    const onHash = () => {
      const r = (window.location.hash || "").replace("#", "");
      if (!r) return;
      // Convenience: #camera / #gallery map to the capture route with a
      // pre-selected sub-stage.
      if (r === "camera") {
        setRoute("capture");
        setState(s => ({ ...s, captureStage: "camera" }));
        return;
      }
      if (r === "gallery") {
        setRoute("capture");
        setState(s => ({ ...s, captureStage: "gallery" }));
        return;
      }
      setRoute(r);
    };
    const onMsg = (e) => {
      const m = e && e.data;
      if (!m || m.type !== "lm-set-stage") return;
      // Preview pages can postMessage({type:'lm-set-stage', stage, mode}) to
      // jump straight to camera / gallery / analyzing / ready.
      setRoute("capture");
      setState(s => ({
        ...s,
        captureStage: m.stage || "camera",
        captureMode:  m.mode  || s.captureMode,
      }));
    };
    window.addEventListener("hashchange", onHash);
    window.addEventListener("message", onMsg);
    return () => {
      window.removeEventListener("hashchange", onHash);
      window.removeEventListener("message", onMsg);
    };
  }, []);

  const go = name => {
    // Named routes "camera" and "gallery" are convenience shortcuts that
    // resolve to the capture route with the matching sub-stage.
    if (name === "camera") {
      setRoute("capture");
      setState(s => ({ ...s, captureStage: "camera", captures: [] }));
      try { window.location.hash = "camera"; } catch (e) {}
      return;
    }
    if (name === "gallery") {
      setRoute("capture");
      setState(s => ({ ...s, captureStage: "gallery", captureMode: "multi", captures: [] }));
      try { window.location.hash = "gallery"; } catch (e) {}
      return;
    }
    if (name === "vision") {
      setRoute("vision");
      try { window.location.hash = "vision"; } catch (e) {}
      return;
    }
    if (name === "chatbot") { setRoute("chat"); try { window.location.hash = "chat"; } catch (e) {} return; }
    if (name === "menu")    { setMenuOpen(true); return; }
    setRoute(name);
    // Re-entering the capture tab always starts at the camera (unless we're
    // mid-flow — but the bottom tab is treated as "fresh start").
    if (name === "capture") {
      setState(s => ({ ...s, captureStage: "camera", captures: [] }));
    }
    try { window.location.hash = name; } catch (e) {}
  };

  // Bottom-tab visibility — hidden on onboarding, review, and the
  // immersive camera + gallery + preview surfaces.
  const hideTabs =
    ["onboarding", "review"].includes(route) ||
    (route === "capture" && ["preview", "analyzing"].includes(state.captureStage));
  const showTabs = !hideTabs;
  const tabValue =
    route === "vision"   ? "vision" :
    route === "capture"  ? "vision" :
    route === "chat"     ? "chatbot" :
    route === "community"? "community" :
    route === "menulist" ? "menu" :
    null;

  let screen;
  switch (route) {
    case "onboarding":
      screen = <OnboardingFlow   state={state} setState={setState} go={go} />; break;
    case "home":
      screen = <DashboardScreen  state={state} setState={setState} go={go} />; break;
    case "vision":
      screen = <VisionLanding    state={state} setState={setState} go={go} />; break;
    case "capture":
    case "camera":
    case "gallery":
      screen = <CaptureScreen    state={state} setState={setState} go={go} />; break;
    case "review":
      screen = <ReviewScreen     state={state} setState={setState} go={go} />; break;
    case "chat":
      screen = <ChatScreen       state={state} setState={setState} go={go} />; break;
    case "consent":
      screen = <ConsentScreen    state={state} setState={setState} go={go} />; break;
    case "community":
      screen = <CommunityScreen  go={go} />; break;
    case "menulist":
      screen = <MenuListScreen   go={go} />; break;
    case "suppdb":
      screen = <SupplementDBScreen />; break;
    case "fooddb":
      screen = <FoodDBScreen />; break;
    default:
      screen = <DashboardScreen  state={state} setState={setState} go={go} />;
  }

  return (
    <div data-screen-label={`${routeLabel(route)}`} style={{ position: "relative", height: "100%" }}>
      {screen}
      {showTabs && (
        <BottomTabs
          value={tabValue}
          onChange={id => go(id)}
          onPlus={() => setPaletteOpen(true)}
        />
      )}
      <PaletteSheet open={paletteOpen} onClose={() => setPaletteOpen(false)} go={go} />
      <HamburgerDrawer open={menuOpen} onClose={() => setMenuOpen(false)} go={go} />
    </div>
  );
}

function routeLabel(r) {
  return ({
    onboarding: "01 Onboarding",
    home:       "02 Dashboard",
    capture:    "03 Capture",
    review:     "04 Review",
    chat:       "05 Chat",
    consent:    "06 Consent",
  })[r] || r;
}

// Render: a single IOSDevice frame containing the App.
ReactDOM.createRoot(document.getElementById("device-host")).render(
  <IOSDevice width={402} height={870}>
    <App />
  </IOSDevice>
);
