/* Nhà Sách Trí Tri – JavaScript dùng chung.
 * Không có script viết trực tiếp trong HTML, nên Content-Security-Policy được phép chặn mọi inline script
 * (giảm nguy cơ XSS). */
(function () {
  "use strict";

  // 1. Hộp xác nhận cho các form nguy hiểm: <form data-confirm="Nội dung câu hỏi">
  document.addEventListener("submit", function (event) {
    var message = event.target.getAttribute("data-confirm");
    if (message && !window.confirm(message)) {
      event.preventDefault();
    }
  });

  // 2. Tự ẩn thông báo thành công / thông tin sau 6 giây (thông báo lỗi giữ nguyên để người dùng đọc kỹ).
  window.setTimeout(function () {
    document.querySelectorAll(".flash-success, .flash-info").forEach(function (flash) {
      flash.classList.add("flash-hide");
      window.setTimeout(function () { flash.remove(); }, 400);
    });
  }, 6000);

  // 3. Đếm ngược ở trang xem quảng cáo: <div data-ad-countdown data-total="15" data-remaining="15">
  var ad = document.querySelector("[data-ad-countdown]");
  if (ad) {
    var total = Number(ad.getAttribute("data-total"));
    var remaining = Number(ad.getAttribute("data-remaining"));
    var label = ad.querySelector("[data-ad-label]");
    var bar = ad.querySelector("[data-ad-bar]");
    var button = ad.querySelector("[data-ad-finish]");
    var tick = function () {
      bar.style.width = ((total - remaining) / total * 100) + "%";
      if (remaining <= 0) {
        label.textContent = "đã xem xong";
        button.disabled = false;
        return;
      }
      label.textContent = remaining + " giây";
      remaining -= 1;
      window.setTimeout(tick, 1000);
    };
    tick();
  }
})();
