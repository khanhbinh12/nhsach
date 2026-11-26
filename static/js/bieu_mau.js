(function () {
  "use strict";

  document.documentElement.classList.add("co-js");

  var SVG_NS = "http://www.w3.org/2000/svg";

  function dinhDangTien(so) {
    var n = parseInt(so, 10);
    if (isNaN(n)) n = 0;
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".") + " đ";
  }

  function layCsrf(form) {
    if (form) {
      var inp = form.querySelector('input[name="csrf"]');
      if (inp && inp.value) return inp.value;
    }
    return (document.body && document.body.getAttribute("data-csrf")) || "";
  }

  function capNhatSoGio(soMoi) {
    var n = parseInt(soMoi, 10);
    if (isNaN(n) || n < 0) n = 0;
    var dsDem = document.querySelectorAll(".nut-gio__dem");
    for (var i = 0; i < dsDem.length; i++) {
      dsDem[i].textContent = String(n);
      dsDem[i].classList.toggle("nut-gio__dem--rong", n === 0);
    }
    var dsLink = document.querySelectorAll(".nut-gio");
    for (var j = 0; j < dsLink.length; j++) {
      dsLink[j].setAttribute("aria-label", "Giỏ hàng hiện có " + n + " sản phẩm");
    }
  }

  var _henTatToast = null;
  function hienThongBaoNoi(loai, noiDung, coNutDat) {
    var khung = document.getElementById("thong-bao-noi");
    if (!khung) return;
    if (_henTatToast) {
      window.clearTimeout(_henTatToast);
      _henTatToast = null;
    }
    khung.innerHTML = "";

    var hop = document.createElement("div");
    hop.className = "toast-gio toast-gio--" + (loai === "loi" ? "loi" : "tot");

    var chu = document.createElement("div");
    chu.className = "toast-gio__chu";
    chu.textContent = noiDung;
    hop.appendChild(chu);

    var hanhDong = document.createElement("div");
    hanhDong.className = "toast-gio__hanh-dong";
    if (coNutDat) {
      var aDat = document.createElement("a");
      aDat.href = "/dat-hang";
      aDat.className = "nut nut--chinh nut--nho";
      aDat.textContent = "Đặt hàng ngay";
      hanhDong.appendChild(aDat);

      var aGio = document.createElement("a");
      aGio.href = "/gio";
      aGio.className = "nut nut--phu nut--nho";
      aGio.textContent = "Xem giỏ";
      hanhDong.appendChild(aGio);
    }

    var nutDong = document.createElement("button");
    nutDong.type = "button";
    nutDong.className = "toast-gio__dong";
    nutDong.setAttribute("aria-label", "Đóng thông báo");
    nutDong.textContent = "×";
    nutDong.addEventListener("click", function () {
      khung.innerHTML = "";
    });
    hanhDong.appendChild(nutDong);
    hop.appendChild(hanhDong);
    khung.appendChild(hop);

    function henTat() {
      _henTatToast = window.setTimeout(function () {
        khung.innerHTML = "";
      }, 6500);
    }
    hop.addEventListener("mouseenter", function () {
      if (_henTatToast) window.clearTimeout(_henTatToast);
    });
    hop.addEventListener("mouseleave", henTat);
    henTat();
  }

  function guiThemGioJson(ma, soLuong, csrf, nutNut) {
    var fd = new FormData();
    fd.append("csrf", csrf);
    fd.append("ma", String(ma));
    fd.append("so_luong", String(soLuong || 1));

    var nhanCu = null;
    if (nutNut) {
      nhanCu = nutNut.textContent;
      nutNut.disabled = true;
      nutNut.setAttribute("aria-busy", "true");
    }

    return window.fetch("/gio/them", {
      method: "POST",
      body: fd,
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (kq) {
        if (kq.data && typeof kq.data.so_trong_gio === "number") {
          capNhatSoGio(kq.data.so_trong_gio);
        }
        if (kq.ok && kq.data && kq.data.ok) {
          var ten = kq.data.ten_sach ? "«" + kq.data.ten_sach + "»" : "sách";
          hienThongBaoNoi("tot", "Đã thêm " + ten + " vào giỏ hàng.", true);
          return true;
        }
        hienThongBaoNoi("loi", (kq.data && kq.data.loi) || "Không thể thêm sách vào giỏ.", false);
        return false;
      })
      .finally(function () {
        if (nutNut) {
          nutNut.disabled = false;
          nutNut.removeAttribute("aria-busy");
          if (nhanCu !== null) nutNut.textContent = nhanCu;
        }
      });
  }

  function taoSvgEl(ten, attrs) {
    var el = document.createElementNS(SVG_NS, ten);
    if (attrs) {
      for (var k in attrs) {
        if (Object.prototype.hasOwnProperty.call(attrs, k)) {
          el.setAttribute(k, String(attrs[k]));
        }
      }
    }
    return el;
  }

  function dungBiaGoiY(muc) {
    var boc = document.createElement("span");
    boc.className = "goi-y-muc__bia";
    if (muc.anh_bia) {
      var img = document.createElement("img");
      img.className = "goi-y-muc__anh";
      img.src = muc.anh_bia;
      img.alt = "";
      img.loading = "lazy";
      boc.appendChild(img);
      return boc;
    }

    var mau = muc.mau_bia || "#2b4c7e";
    var bia = muc.bia || {};
    var mauChu = bia.mau_chu || "#ffffff";
    var khuon = bia.khuon || "hien_dai";
    var dong = Array.isArray(bia.dong_tieu_de) && bia.dong_tieu_de.length
      ? bia.dong_tieu_de.slice(0, 2)
      : [(muc.tieu_de || "Sách").slice(0, 12)];

    var svg = taoSvgEl("svg", {
      viewBox: "0 0 240 360",
      class: "goi-y-muc__svg",
      "aria-hidden": "true",
    });
    svg.appendChild(taoSvgEl("rect", { width: 240, height: 360, fill: mau }));
    svg.appendChild(taoSvgEl("rect", { x: 0, y: 0, width: 24, height: 360, fill: "#000000", "fill-opacity": "0.22" }));

    if (khuon === "co_dien") {
      svg.appendChild(taoSvgEl("rect", {
        x: 32, y: 24, width: 188, height: 312, rx: 6, fill: "none",
        stroke: mauChu, "stroke-opacity": "0.45", "stroke-width": 5,
      }));
    } else if (khuon === "ky_nang") {
      svg.appendChild(taoSvgEl("rect", { x: 24, y: 0, width: 216, height: 42, fill: mauChu, "fill-opacity": "0.16" }));
    } else if (khuon === "thieu_nhi") {
      svg.appendChild(taoSvgEl("rect", {
        x: 32, y: 24, width: 188, height: 312, rx: 24, fill: "none",
        stroke: mauChu, "stroke-opacity": "0.45", "stroke-width": 5, "stroke-dasharray": "12 10",
      }));
    } else {
      svg.appendChild(taoSvgEl("polygon", { points: "126,0 240,0 240,120", fill: mauChu, "fill-opacity": "0.16" }));
    }

    var text = taoSvgEl("text", {
      x: 130,
      y: dong.length > 1 ? 166 : 194,
      "text-anchor": "middle",
      fill: mauChu,
      "font-size": 30,
      "font-weight": 800,
    });
    for (var i = 0; i < dong.length; i++) {
      var ts = taoSvgEl("tspan", { x: 130, dy: i === 0 ? 0 : 42 });
      ts.textContent = String(dong[i]).slice(0, 14);
      text.appendChild(ts);
    }
    svg.appendChild(text);
    boc.appendChild(svg);
    return boc;
  }

  function khoiTaoGoiYTimKiem() {
    var khung = document.querySelector("[data-goi-y-tim]");
    if (!khung) return;
    var input = khung.querySelector("#o-tim-sach");
    var danhSach = khung.querySelector("#goi-y-tim-sach");
    if (!input || !danhSach) return;

    var timer = null;
    var controller = null;
    var mucHienTai = [];
    var chiSoChon = -1;

    function dongGoiY() {
      danhSach.hidden = true;
      danhSach.innerHTML = "";
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
      mucHienTai = [];
      chiSoChon = -1;
    }

    function capNhatChon(moi) {
      var cacDong = danhSach.querySelectorAll('[role="option"]');
      if (!cacDong.length) {
        chiSoChon = -1;
        input.removeAttribute("aria-activedescendant");
        return;
      }
      if (moi < -1) moi = cacDong.length - 1;
      if (moi >= cacDong.length) moi = -1;
      chiSoChon = moi;
      for (var i = 0; i < cacDong.length; i++) {
        var chon = i === chiSoChon;
        cacDong[i].setAttribute("aria-selected", chon ? "true" : "false");
        cacDong[i].classList.toggle("goi-y-muc--chon", chon);
      }
      if (chiSoChon >= 0) {
        var el = cacDong[chiSoChon];
        input.setAttribute("aria-activedescendant", el.id);
        if (typeof el.scrollIntoView === "function") {
          el.scrollIntoView({ block: "nearest" });
        }
      } else {
        input.removeAttribute("aria-activedescendant");
      }
    }

    function veGoiY(q, ds) {
      danhSach.innerHTML = "";
      mucHienTai = ds || [];
      chiSoChon = -1;
      input.removeAttribute("aria-activedescendant");

      if (!mucHienTai.length) {
        var trong = document.createElement("div");
        trong.className = "goi-y-tim__trong";
        trong.textContent = "Không tìm thấy sách khớp «" + q + "»";
        danhSach.appendChild(trong);
        danhSach.hidden = false;
        input.setAttribute("aria-expanded", "true");
        return;
      }

      var csrf = layCsrf(null);
      for (var i = 0; i < mucHienTai.length; i++) {
        (function (muc, idx) {
          var dong = document.createElement("div");
          dong.className = "goi-y-muc";
          dong.setAttribute("role", "option");
          dong.id = "goi-y-muc-" + idx;
          dong.setAttribute("aria-selected", "false");
          dong.setAttribute("data-url", "/sach/" + muc.ma);

          var link = document.createElement("a");
          link.className = "goi-y-muc__link";
          link.href = "/sach/" + muc.ma;
          link.setAttribute("tabindex", "-1");
          link.appendChild(dungBiaGoiY(muc));

          var info = document.createElement("span");
          info.className = "goi-y-muc__thong-tin";

          var ten = document.createElement("span");
          ten.className = "goi-y-muc__ten";
          ten.textContent = muc.tieu_de;
          info.appendChild(ten);

          var phu = document.createElement("span");
          phu.className = "goi-y-muc__phu";
          phu.textContent = muc.tac_gia + " • " + dinhDangTien(muc.gia);
          info.appendChild(phu);

          link.appendChild(info);
          dong.appendChild(link);

          if (muc.con_hang) {
            var nutGio = document.createElement("button");
            nutGio.type = "button";
            nutGio.className = "nut nut--vien-nhan nut--nho goi-y-muc__gio";
            nutGio.textContent = "+ Giỏ";
            nutGio.setAttribute("aria-label", "Thêm " + muc.tieu_de + " vào giỏ");
            nutGio.addEventListener("click", function (ev) {
              ev.preventDefault();
              ev.stopPropagation();
              guiThemGioJson(muc.ma, 1, csrf, nutGio);
            });
            dong.appendChild(nutGio);
          } else {
            var het = document.createElement("span");
            het.className = "nhan nhan--trung-tinh";
            het.textContent = "Hết hàng";
            dong.appendChild(het);
          }

          dong.addEventListener("mouseenter", function () {
            capNhatChon(idx);
          });
          danhSach.appendChild(dong);
        })(mucHienTai[i], i);
      }

      var chan = document.createElement("a");
      chan.className = "goi-y-tim__tat-ca";
      chan.href = "/sach?q=" + encodeURIComponent(q);
      chan.textContent = "Xem tất cả kết quả cho «" + q + "» →";
      danhSach.appendChild(chan);

      danhSach.hidden = false;
      input.setAttribute("aria-expanded", "true");
    }

    function taiGoiY(q) {
      if (controller && typeof controller.abort === "function") {
        controller.abort();
      }
      controller = typeof AbortController !== "undefined" ? new AbortController() : null;
      var opts = { headers: { Accept: "application/json" }, credentials: "same-origin" };
      if (controller) opts.signal = controller.signal;

      window.fetch("/api/goi-y?q=" + encodeURIComponent(q), opts)
        .then(function (res) {
          if (!res.ok) return [];
          return res.json();
        })
        .then(function (ds) {
          if (input.value.trim() !== q) return;
          veGoiY(q, Array.isArray(ds) ? ds.slice(0, 6) : []);
        })
        .catch(function () {});
    }

    input.addEventListener("input", function () {
      var q = input.value.trim();
      if (timer) window.clearTimeout(timer);
      if (q.length < 2) {
        dongGoiY();
        return;
      }
      timer = window.setTimeout(function () {
        taiGoiY(q);
      }, 200);
    });

    input.addEventListener("keydown", function (e) {
      if (danhSach.hidden) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        capNhatChon(chiSoChon + 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        capNhatChon(chiSoChon - 1);
      } else if (e.key === "Escape") {
        e.preventDefault();
        dongGoiY();
      } else if (e.key === "Enter" && chiSoChon >= 0) {
        var cacDong = danhSach.querySelectorAll('[role="option"]');
        var chonEl = cacDong[chiSoChon];
        var url = chonEl && chonEl.getAttribute("data-url");
        if (url) {
          e.preventDefault();
          window.location.href = url;
        }
      }
    });

    document.addEventListener("click", function (e) {
      if (!khung.contains(e.target)) {
        dongGoiY();
      }
    });
  }

  function khoiTaoCuonDanhMuc() {
    var ds = document.querySelectorAll("[data-cuon-ngang]");
    for (var i = 0; i < ds.length; i++) {
      (function (boc) {
        var ul = boc.querySelector(".menu-danh-muc");
        var nutPhai = boc.querySelector("[data-cuon-phai]");
        if (!ul) return;

        function capNhat() {
          var conPhai = ul.scrollWidth - ul.clientWidth - ul.scrollLeft > 4;
          var conTrai = ul.scrollLeft > 4;
          boc.classList.toggle("co-cuon-phai", conPhai);
          boc.classList.toggle("co-cuon-trai", conTrai);
          if (nutPhai) nutPhai.hidden = !conPhai;
        }

        if (nutPhai) {
          nutPhai.addEventListener("click", function () {
            ul.scrollBy({ left: 260, behavior: "smooth" });
          });
        }
        ul.addEventListener("scroll", capNhat, { passive: true });
        window.addEventListener("resize", capNhat);
        capNhat();
      })(ds[i]);
    }
  }

  function khoiTaoCuonBang() {
    var ds = document.querySelectorAll(".hop-bang > .bang-cuon");
    for (var i = 0; i < ds.length; i++) {
      (function (cuon) {
        var hop = cuon.parentElement;
        if (!hop) return;
        if (!hop.querySelector(".goi-y-cuon-bang")) {
          var goiY = document.createElement("div");
          goiY.className = "goi-y-cuon-bang";
          goiY.setAttribute("aria-hidden", "true");
          goiY.textContent = "Vuốt ngang để xem thêm cột →";
          hop.insertBefore(goiY, cuon);
        }

        function capNhat() {
          var vuot = cuon.scrollWidth - cuon.clientWidth > 4;
          var conPhai = cuon.scrollWidth - cuon.clientWidth - cuon.scrollLeft > 4;
          var conTrai = cuon.scrollLeft > 4;
          hop.classList.toggle("co-cuon-ngang", vuot);
          hop.classList.toggle("co-cuon-phai", conPhai);
          hop.classList.toggle("co-cuon-trai", conTrai);
        }

        cuon.addEventListener("scroll", capNhat, { passive: true });
        window.addEventListener("resize", capNhat);
        capNhat();
      })(ds[i]);
    }
  }

  function khoaNutGui(form, submitter) {
    var nut =
      (submitter && submitter.matches && submitter.matches('button[type="submit"], input[type="submit"]')
        ? submitter
        : null) || form.querySelector('button[type="submit"], input[type="submit"]');
    if (!nut) return;

    var nhanXuLy = nut.getAttribute("data-nhan-xu-ly") || "Đang xử lý…";
    if (!nut.dataset.nhanGoc) {
      nut.dataset.nhanGoc = nut.tagName === "INPUT" ? nut.value : nut.textContent;
    }
    if (nut.tagName === "INPUT") {
      nut.value = nhanXuLy;
    } else {
      nut.textContent = nhanXuLy;
    }
    nut.setAttribute("aria-busy", "true");
    form.setAttribute("aria-busy", "true");
    // Trì hoãn disabled sau nhịp submit để trình duyệt vẫn gửi name/value của nút bấm.
    window.setTimeout(function () {
      if (form.dataset.daGui === "1") {
        nut.disabled = true;
      }
    }, 0);
  }

  function moKhoaForm(form) {
    delete form.dataset.daGui;
    form.removeAttribute("aria-busy");
    var nut = form.querySelector('button[type="submit"], input[type="submit"]');
    if (!nut) return;
    nut.disabled = false;
    nut.removeAttribute("aria-busy");
    if (nut.dataset.nhanGoc) {
      if (nut.tagName === "INPUT") {
        nut.value = nut.dataset.nhanGoc;
      } else {
        nut.textContent = nut.dataset.nhanGoc;
      }
    }
  }

  function capNhatTrangThaiStepper(boc) {
    var input = boc.querySelector('input[type="number"]');
    if (!input) return;
    var min = parseInt(input.min, 10);
    if (isNaN(min)) min = 1;
    var max = parseInt(input.max, 10);
    var cur = parseInt(input.value, 10);
    if (isNaN(cur)) cur = min;
    var nutGiam = boc.querySelector("[data-stepper-giam]");
    var nutTang = boc.querySelector("[data-stepper-tang]");
    if (nutGiam) nutGiam.disabled = input.disabled || cur <= min;
    if (nutTang) nutTang.disabled = input.disabled || (!isNaN(max) && cur >= max);
  }

  function khoiTaoStepper() {
    var ds = document.querySelectorAll("[data-stepper]");
    for (var i = 0; i < ds.length; i++) {
      capNhatTrangThaiStepper(ds[i]);
    }
  }

  function chepVanBan(text, xong) {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      navigator.clipboard.writeText(text).then(
        function () { xong(true); },
        function () { xong(chepDuPhong(text)); }
      );
      return;
    }
    xong(chepDuPhong(text));
  }

  function chepDuPhong(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (_err) {
      ok = false;
    }
    document.body.removeChild(ta);
    return ok;
  }

  document.addEventListener("click", function (e) {
    var nutChep = e.target && e.target.closest ? e.target.closest("[data-sao-chep]") : null;
    if (nutChep) {
      var noiDung = nutChep.getAttribute("data-sao-chep") || "";
      if (!noiDung) return;
      if (!nutChep.dataset.nhanGoc) {
        nutChep.dataset.nhanGoc = nutChep.textContent.trim();
      }
      chepVanBan(noiDung, function (ok) {
        if (!ok) return;
        nutChep.textContent = "Đã chép";
        nutChep.classList.add("nut-sao-chep--da-chep");
        if (nutChep._henGio) window.clearTimeout(nutChep._henGio);
        nutChep._henGio = window.setTimeout(function () {
          nutChep.textContent = nutChep.dataset.nhanGoc || "Sao chép";
          nutChep.classList.remove("nut-sao-chep--da-chep");
        }, 2000);
      });
      return;
    }

    var nutStep = e.target && e.target.closest ? e.target.closest("[data-stepper-giam], [data-stepper-tang]") : null;
    if (!nutStep || nutStep.disabled) return;
    var boc = nutStep.closest("[data-stepper]");
    if (!boc) return;
    var input = boc.querySelector('input[type="number"]');
    if (!input || input.disabled) return;

    var min = parseInt(input.min, 10);
    if (isNaN(min)) min = 1;
    var max = parseInt(input.max, 10);
    var cur = parseInt(input.value, 10);
    if (isNaN(cur)) cur = min;

    var laTang = nutStep.hasAttribute("data-stepper-tang");
    var moi;
    if (laTang) {
      moi = isNaN(max) ? cur + 1 : Math.min(max, cur + 1);
    } else {
      moi = !isNaN(max) && cur > max ? Math.max(min, max) : Math.max(min, cur - 1);
    }

    if (moi !== cur) {
      input.value = String(moi);
      capNhatTrangThaiStepper(boc);
      if (boc.hasAttribute("data-stepper-tu-gui")) {
        var form = boc.tagName === "FORM" ? boc : boc.closest("form");
        if (form) form.submit();
      }
    }
  });

  document.addEventListener("change", function (e) {
    var target = e.target;
    if (target && target.matches && target.matches("form[data-tu-gui-chon] select")) {
      var formChon = target.closest("form");
      if (formChon) formChon.submit();
      return;
    }

    var input = target;
    if (!input || !input.matches || !input.matches('[data-stepper] input[type="number"]')) return;
    var boc = input.closest("[data-stepper]");
    if (!boc) return;
    var min = parseInt(input.min, 10);
    if (isNaN(min)) min = 1;
    var max = parseInt(input.max, 10);
    var val = parseInt(input.value, 10);
    if (isNaN(val) || val < min) val = min;
    if (!isNaN(max) && val > max) val = max;
    input.value = String(val);
    capNhatTrangThaiStepper(boc);
    if (boc.hasAttribute("data-stepper-tu-gui")) {
      var form = boc.tagName === "FORM" ? boc : boc.closest("form");
      if (form) form.submit();
    }
  });

  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form || !form.matches) return;

    if (form.hasAttribute("data-gio-them")) {
      if (e.submitter && e.submitter.hasAttribute("data-mua-ngay")) {
        return;
      }
      if (typeof window.fetch === "function") {
        e.preventDefault();
        var maInp = form.querySelector('input[name="ma"]');
        var slInp = form.querySelector('input[name="so_luong"]');
        var csrf = layCsrf(form);
        var nutGui = e.submitter || form.querySelector('button[type="submit"]');
        guiThemGioJson(maInp ? maInp.value : "", slInp ? slInp.value : 1, csrf, nutGui).catch(function () {
          form.removeAttribute("data-gio-them");
          form.submit();
        });
        return;
      }
    }

    if (form.hasAttribute("data-xac-nhan")) {
      var loiHoi = form.getAttribute("data-xac-nhan") || "Bạn có chắc muốn thực hiện thao tác này?";
      if (!window.confirm(loiHoi)) {
        e.preventDefault();
        return;
      }
    }

    if (!form.matches("form[data-dang-xu-ly]")) return;
    if (e.submitter && e.submitter.hasAttribute("data-khong-khoa")) return;
    if (form.dataset.daGui === "1") {
      e.preventDefault();
      return;
    }
    if (typeof form.checkValidity === "function" && !form.checkValidity()) {
      return;
    }
    form.dataset.daGui = "1";
    khoaNutGui(form, e.submitter);
  });

  window.addEventListener("pageshow", function (e) {
    if (!e.persisted) return;
    var ds = document.querySelectorAll("form[data-dang-xu-ly]");
    for (var i = 0; i < ds.length; i++) {
      moKhoaForm(ds[i]);
    }
  });

  function khoiTaoTatCa() {
    khoiTaoStepper();
    khoiTaoGoiYTimKiem();
    khoiTaoCuonDanhMuc();
    khoiTaoCuonBang();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", khoiTaoTatCa);
  } else {
    khoiTaoTatCa();
  }
})();
