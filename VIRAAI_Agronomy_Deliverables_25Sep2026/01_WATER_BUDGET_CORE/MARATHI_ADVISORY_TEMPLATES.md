# Marathi Advisory Templates — Irrigation Messages (WhatsApp / App)

**उद्देश:** Backend Water Budget engine + VWC-based D03 rules ने trigger केलेल्या advisories साठी Marathi templates. Language principle: **साधी, बोलीभाषेतील Marathi** — शेतकऱ्याला एका नजरेत काय करायचं ते कळावं. English loanwords (sensor, drip) रुजलेले असल्याने ठेवले.

**Version:** 1.0
**Date:** 25 September 2026
**Owner:** Kuldip — Agronomy Compliance Owner

**Format:** प्रत्येक template मध्ये `{variable}` म्हणजे backend भरून देणारं value. सर्व templates ला एक footer आहे — त्यात contributing_signals + confidence + evidence link.

---

## Template 1 — सामान्य सिंचन शिफारस (normal irrigation)

**Trigger:** Multi-signal engine says irrigate (urgency = normal). VWC low OR water-budget deficit ≥ 25%, no red flags.

```
🌱 आजची सिंचन शिफारस — {plot_name}

आपल्या शेतासाठी आज:
💧 पाणी: {dose_L_per_plot} लिटर
⏱️ वेळ: {duration_min} मिनिटे drip चालवा

का?
- सब-नोड sensor: माती {vwc_status_mr}
- पाणी-लेखा: या अवस्थेत ({stage_name_mr}) आतापर्यंत {per_plant_water_so_far} लिटर/रोप मिळाले;
  गरज होती {stage_target} लिटर/रोप — तूट भरून काढा

Confidence: {confidence_label} ({confidence_pct}%)
Signals: {signals_list_mr}
```

**VWC status translations:**
- `low` → कोरडी झाली आहे
- `ok` → योग्य आहे
- `saturated` → संपृक्त (जास्त ओलावा)

**Stage name translations:**
- G1 → स्थापना अवस्था
- G2 → वाढीची अवस्था
- G3 → गड्डा-निर्मिती अवस्था
- G4 → गड्डा-भरणी अवस्था
- G5 → परिपक्वता अवस्था

**Signals list translations:**
- vwc_probe → सब-नोड ओलावा
- water_budget → पाणी-लेखा
- weather_forecast → हवामान अंदाज
- satellite_ndmi → उपग्रह
- stage_context → अवस्था

---

## Template 2 — दोन्ही signals सहमत (VWC + water-budget both trigger)

**Trigger:** VWC low AND water-budget deficit ≥ 30%. BUNDLES-precedence — one message.

```
🌱 आजची सिंचन शिफारस — {plot_name}

💧 पाणी: {dose_L_per_plot} लिटर
⏱️ वेळ: {duration_min} मिनिटे drip चालवा

का?
- सब-नोड sensor: माती कोरडी झाली
- पाणी-लेखा: तूट {deficit_pct}%
- दोन्ही sensors एकाच वेळी पाणी देण्याचा संकेत देत आहेत — त्यामुळे शिफारस अधिक विश्वासार्ह

Confidence: High ({confidence_pct}%)
Signals: सब-नोड ओलावा + पाणी-लेखा
```

---

## Template 3 — लाल इशारा (RED urgency — critical deficit in G3)

**Trigger:** G3 stage + water-budget deficit ≥ 40%, OR heat modifier bumped urgency to red.

```
⚠️ लाल इशारा — तात्काळ सिंचन गरजेचे

शेत: {plot_name}
अवस्था: गड्डा-निर्मिती (G3) — सर्वात संवेदनशील काळ

आत्ता करा:
💧 पाणी: {dose_L_per_plot} लिटर
⏱️ वेळ: {duration_min} मिनिटे drip चालवा
🕐 उशीर: आजच द्या — उद्यापर्यंत थांबू नका

का?
- पाणी-लेखा: तूट {deficit_pct}% — मोठा तुटवडा
- सब-नोड sensor: {vwc_status_mr}
{IF heat_flag} - तापमान {air_temp_max_c}°C — दुपारी उन्ह वाढत आहे {ENDIF}
- गड्डा-निर्मितीच्या अवस्थेत पाणी न मिळाल्यास उत्पादनावर परिणाम होतो

Confidence: High ({confidence_pct}%)
Signals: {signals_list_mr}
```

---

## Template 4 — पाणी थांबवा (VWC saturated override)

**Trigger:** VWC probe reads saturation, regardless of water-budget signal. D03-MN-002 SUPPRESSES water-budget.

```
🛑 आज पाणी देऊ नका — {plot_name}

सब-नोड sensor दाखवते: मातीत पाणी संपृक्त (खूप ओलावा).
आजचा दिवस थांबा — उद्या परत तपासू.

महत्त्वाचे: पाणी-लेखानुसार तूट वाटत असली तरी sensor वर विश्वास ठेवा —
जमिनीत खरा ओलावा किती हे probe ला exactly कळते.

जास्त पाणी दिल्यास गड्डा-कूज (rhizome rot) आणि जिवाणू-मर (bacterial wilt) 
यांचा धोका वाढतो.

Confidence: High (95%)
Signal: सब-नोड ओलावा (VWC probe)
```

---

## Template 5 — आज पाऊस अपेक्षित (rain forecast override)

**Trigger:** `forecast_rain_48h_mm >= 25` AND stage != G5.

```
☔ आज सिंचन नको — {plot_name}

पुढील ४८ तासांत {rain_mm} मिमी पाऊस अपेक्षित आहे.
पाऊसच अद्रकीला पाणी देईल — आज drip चालवण्याची गरज नाही.

पाऊस पडल्यानंतर:
- पाऊस झाल्यावर सब-नोड sensor परत तपासेल
- पुढील शिफारस उद्या-परवा app वर येईल

Confidence: {confidence_pct}% (हवामान अंदाजावर अवलंबून)
Signal: हवामान अंदाज
```

---

## Template 6 — VWC आणि water-budget विरोधाभास (conflict flag)

**Trigger:** VWC OK but water-budget shows over-irrigation. Suggests drip malfunction or drainage failure.

```
⚠️ शेतफेरी करा — {plot_name}

काहीतरी विसंगती दिसत आहे:
- सब-नोड sensor: माती ओलावा योग्य आहे
- पाणी-लेखा: गरजेपेक्षा जास्त पाणी दिले गेले

संभाव्य कारण:
1. Drip नळी कुठेतरी बंद (blocked) असू शकते — पाणी sensor पर्यंत पोहोचत आहे 
   पण नंतर बाहेर पडत नाही
2. निचरा-समस्या — पाणी साठून राहत आहे
3. एका भागाला जास्त, दुसऱ्या भागाला कमी पाणी जात असेल

आज करा:
- शेतफेरी करून drip नळ्या तपासा
- कोणत्या भागात पाणी साठले आहे का बघा
- सर्व drippers नीट चालतात का तपासा

Confidence: Medium
Signals: सब-नोड ओलावा + पाणी-लेखा (विरोधाभास)
```

---

## Template 7 — Sensor गप्प आहे (sensor gap alert)

**Trigger:** `days_since_last_reading > 3` for water flow sensor.

```
⚠️ Sensor तपासा — {plot_name}

{sensor_gap_days} दिवसांपासून water flow sensor कडून reading आले नाही.

काय झाले असू शकते:
- Sensor battery संपली
- Sensor नळीवरून सुटला किंवा तुटला
- Network / connectivity प्रश्न

आत्ता करा:
- शेतात जाऊन sensor तपासा
- Battery / connections नीट आहेत का बघा
- गरज असल्यास technician ला call करा

तोपर्यंत:
- सब-नोड ओलावा sensor वरून पाणी शिफारसी चालू राहतील
- "किती लिटर" quantitative शिफारस तात्पुरती थांबवली आहे 
  (water flow sensor परत सुरू झाल्यावर परत सुरू होईल)

Confidence: N/A (sensor गप्प)
Signal: hardware alert
```

---

## Template 8 — G5 अवस्थेत सिंचन थांबवा (senescence stage)

**Trigger:** Stage = G5 (DAP 210+) — approaching harvest.

```
🌾 काढणीची तयारी — {plot_name}

अद्रक आता परिपक्वता अवस्थेत (G5) आहे. काढणी 15-20 दिवसांत.

आजच सिंचन थांबवा:
- पाणी दिल्यास गड्ड्याची साल कमजोर राहते
- Storage life कमी होते
- सुकवण्याचा त्रास वाढतो

पुढील 15-20 दिवस:
- पाऊस पडला तरच पाणी मिळेल
- गड्डा नैसर्गिकरित्या "curing" होईल
- साल टणक, चमकदार, टिकाऊ होईल

काढणीची तयारी:
- Storage जागा तयार करा
- Grading आणि cleaning साठी मजूर ठरवा
- Market rates तपासा

Signal: अवस्था (G5)
```

---

## Template 9 — Confidence कमी (guidance-only tag)

**Trigger:** `water_budget_confidence < 0.60` — one or more signal degradations.

```
💧 आजची सिंचन शिफारस — {plot_name} (मार्गदर्शन)

आपल्या शेतासाठी आजची अंदाजे शिफारस:
💧 पाणी: {dose_L_per_plot} लिटर
⏱️ वेळ: {duration_min} मिनिटे

⚠️ नोंद: सध्या sensor / geometry माहितीत काही अंतर आहे, त्यामुळे ही शिफारस 
"मार्गदर्शन" म्हणून घ्या — 100% अचूक नाही.

अचूक शिफारसीसाठी:
{IF geometry_incomplete} - Planting geometry पूर्ण भरा (app मध्ये "बदल करा") {ENDIF}
{IF sensor_position_unknown} - Sensor position सांगा (app मध्ये update करा) {ENDIF}
{IF flow_telemetry_missing} - Water flow sensor तपासा {ENDIF}

Confidence: Low ({confidence_pct}%)
```

---

## Template 10 — Farmer override acknowledgement

**Trigger:** Farmer manually logged irrigation event through app (before/instead of system recommendation).

```
✅ आपल्या सिंचनाची नोंद घेतली — {plot_name}

आपण दिलेली माहिती:
💧 पाणी: {farmer_reported_L} लिटर
⏱️ वेळ: {farmer_reported_min} मिनिटे
📅 वेळ: {timestamp}

का दिले: {reason_enum_mr}

System-ची शिफारस {IF differs}(जी {system_dose_L} लिटर होती){ENDIF} update केली.
पुढील शिफारसीसाठी हा data वापरला जाईल.

धन्यवाद — आपल्या feedback मुळे system सुधारते.
```

**Reason enum translations:**
- `already_irrigated` → आधीच पाणी दिले होते
- `different_reason` → वेगळ्या कारणासाठी दिले
- `disagreed` → शिफारसीशी असहमत
- `other` → इतर कारण

---

## Common footer (सर्व messages ला जोडा — small print)

```
─────────────
📱 App मध्ये details पहा: {evidence_link}
🔔 Confidence: {conf_label}
📞 अडचण? Agronomist ला call करा: {helpline_number}
```

---

## Language guidance summary

**Do ✅:**
- साधी, बोलीभाषेतील Marathi
- English loanwords (sensor, drip, pipe, WhatsApp, app) रुजलेले असल्याने ठेवा
- सर्व numbers शेतकऱ्याला useful (लिटर, मिनिटे, तास, दिवस)
- Emoji sparingly — फक्त heading + क्रिया दर्शवायला
- अवस्था / dose / वेळ ठळक (bold) करा app मध्ये

**Don't ❌:**
- अति शुद्ध Sanskrit-derived Marathi (~~संवेदक~~, ~~बिंदुसिंचन~~)
- अति शेतकी jargon न-explained
- लांब पॅरा — bullet points + अंतर वापरा
- Farmer ला blame करणारी भाषा
- Sensor readings raw numbers दाखवणे (VWC 42.3% इ.) — translate करा ("माती योग्य ओलाव्यात")

**Regional considerations:**
- "सरी" / "पाट" — Marathwada + Vidarbha "सरी" वापरतात; Konkan-वर "पाट" — helper text मध्ये दोन्ही एकदा clarify
- "गड्डा" — ginger rhizome; सर्वत्र समजतो
- "काळी माती" — vertisol; universally understood

---

*End of Marathi Advisory Templates v1.0*
