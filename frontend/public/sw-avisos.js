// Se importa en el service worker de la PWA: al tocar un recordatorio, abre (o enfoca) la reserva.
self.addEventListener("notificationclick", (evento) => {
  evento.notification.close();
  const url = (evento.notification.data && evento.notification.data.url) || "/";
  evento.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((ventanas) => {
      for (const v of ventanas) {
        if ("focus" in v) { v.navigate(url); return v.focus(); }
      }
      return self.clients.openWindow(url);
    }),
  );
});
