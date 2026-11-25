/* ─── MEDICIÓN · un solo lugar ─────────────────────────────
   Lo cargan / y /diagnostico en el <head>.

   1. Vercel Web Analytics: visitas y fuentes. Se activa en Vercel →
      proyecto privatebuild → Analytics. En plan Hobby no recibe eventos
      propios; esos van a PostHog.
   2. PostHog: el embudo del diagnóstico. pvtTrack() (en
      diagnostico/index.html) manda cada evento apenas window.posthog existe.
      Para encenderlo: pegar la Project API Key (phc_…) abajo. Es una
      llave pública, puede vivir en el código. Si el proyecto se creó en la
      región EU, cambiar el host a https://eu.i.posthog.com.
   Sin key no se carga nada de PostHog y los eventos siguen quedando en
   localStorage (pb_eventos), como antes. */

var PVT_POSTHOG_KEY  = '';                          // phc_…
var PVT_POSTHOG_HOST = 'https://us.i.posthog.com';

(function () {
  // Vercel Web Analytics
  try {
    window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
    var v = document.createElement('script');
    v.defer = true;
    v.src = '/_vercel/insights/script.js';
    document.head.appendChild(v);
  } catch (e) {}

  // PostHog (solo con key)
  if (!PVT_POSTHOG_KEY) return;
  !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags on onFeatureFlags onSessionId identify setPersonProperties group resetGroups reset get_distinct_id getGroups get_session_id alias set_config startSessionRecording stopSessionRecording captureException get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing debug".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
  window.posthog.init(PVT_POSTHOG_KEY, {
    api_host: PVT_POSTHOG_HOST,
    person_profiles: 'identified_only',
    capture_pageview: true
  });
})();
