import axios from "axios";
import cheerio from "cheerio";
import nodemailer from "nodemailer";
import fs from "fs";

const EMAIL_TO = "vinavil80@gmail.com";

// Configura qui le ricerche
const ricerche = [
  { keyword: "thorens", prezzoMax: 200 },
  { keyword: "stephen king ossessione", prezzoMax: 15 },
  { keyword: "kartell", prezzoMax: 150 }
];

const fileMemoria = "prodotti_notificati.json";

// Carica memoria
let notificati = [];
if (fs.existsSync(fileMemoria)) {
  notificati = JSON.parse(fs.readFileSync(fileMemoria));
}

// Config email (usa Gmail con App Password)
const transporter = nodemailer.createTransport({
  service: "gmail",
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASS
  }
});

async function controlla() {

  for (let r of ricerche) {

    const query = r.keyword.replace(/\s+/g, "-");
    const url = `https://www.mercatinousato.com/search/prod/${query}`;

    console.log("Controllo:", r.keyword);

    try {

      const { data } = await axios.get(url, {
        headers: {
          "User-Agent": "Mozilla/5.0"
        }
      });

      const $ = cheerio.load(data);

      $(".list-product-minibox").each(async (i, el) => {

        if ($(el).text().includes("VENDUTO")) return;

        const prezzo = parseFloat($(el).find('[itemprop="price"]').attr("content"));
        const link = $(el).find('[itemprop="url"]').attr("content");
        const titolo = $(el).find(".list-product-title span").text().trim();

        if (!prezzo || !link) return;

        if (prezzo <= r.prezzoMax && !notificati.includes(link)) {

          console.log("MATCH:", titolo);

          await transporter.sendMail({
            from: process.env.EMAIL_USER,
            to: EMAIL_TO,
            subject: "Nuovo prodotto trovato",
            html: `
              <b>${titolo}</b><br>
              Prezzo: € ${prezzo}<br>
              <a href="${link}">Apri annuncio</a>
            `
          });

          notificati.push(link);
          fs.writeFileSync(fileMemoria, JSON.stringify(notificati, null, 2));
        }

      });

    } catch (err) {
      console.log("Errore:", err.message);
    }

  }
}

controlla();
