self.addEventListener("push", (event) => {
  if (!event.data) return;
  const payload = event.data.json();
  event.waitUntil(
    self.registration.showNotification(payload.title || "Fashion Data Engine", {
      body: payload.body || "새 알림이 도착했습니다.",
      data: { url: payload.url || "/feed" },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/feed";
  event.waitUntil(clients.openWindow(targetUrl));
});
