import smtplib
from email.message import EmailMessage
from config import SENDER_EMAIL, SENDER_PASSWORD

def send_personalized_email(email, name, station, stats_full, global_maps, station_charts):
    msg = EmailMessage()
    msg['Subject'] = f" DASHBOARD MÉTÉO - {station}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = email

   
    avg_t = round(stats_full['t_pred'].mean(), 1)
    avg_f = round(stats_full['ff_pred'].mean(), 1)
    avg_r = round(stats_full['rr1_pred'].sum(), 1)

    html = f"""
    <html>
    <body style="font-family: 'Segoe UI', sans-serif; background-color: #f4f7f6; color: #2c3e50; padding: 20px;">
        <div style="max-width: 700px; margin: auto; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
            <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; color: white; text-align: center;">
                <h1 style="margin: 0;">MÉTÉO CORSE CONNECTÉE</h1>
                <p style="opacity: 0.8;">Rapport Premium pour {name}</p>
            </div>

            <div style="padding: 30px;">
                <h2 style="border-bottom: 2px solid #eee; padding-bottom: 10px;">📊 RÉSUMÉ 24H - {station}</h2>
                <div style="display: flex; justify-content: space-around; margin: 20px 0;">
                    <div style="text-align: center;"><b>MOY. TEMP</b><br><span style="font-size: 24px; color: #ff4b2b;">{avg_t}°C</span></div>
                    <div style="text-align: center;"><b>MOY. VENT</b><br><span style="font-size: 24px; color: #00d2ff;">{avg_f} km/h</span></div>
                    <div style="text-align: center;"><b>CUMUL PLUIE</b><br><span style="font-size: 24px; color: #2ecc71;">{avg_r} mm</span></div>
                </div>

                <h3>📈 TENDANCES LOCALES</h3>
                <img src="cid:chart_t" style="width: 100%; margin-bottom: 15px; border-radius: 8px;">
                <img src="cid:chart_ff" style="width: 100%; margin-bottom: 15px; border-radius: 8px;">
                <img src="cid:chart_rr1" style="width: 100%; margin-bottom: 15px; border-radius: 8px;">

                <h3 style="margin-top: 40px;">🗺️ SITUATION RÉGIONALE (CORSE)</h3>
                <div style="text-align: center;">
                    <img src="cid:map_t" style="width: 31%; border-radius: 5px;">
                    <img src="cid:map_ff" style="width: 31%; border-radius: 5px;">
                    <img src="cid:map_rr1" style="width: 31%; border-radius: 5px;">
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    msg.set_content(html, subtype='html')

    for var, path in station_charts.items():
        with open(path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='image', subtype='png', cid=f'chart_{var}')

    for var, path in global_maps.items():
        with open(path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='image', subtype='png', cid=f'map_{var}')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(SENDER_EMAIL, SENDER_PASSWORD)

        smtp.send_message(msg)

