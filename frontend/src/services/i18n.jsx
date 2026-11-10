/**
 * i18n.jsx - English / اردو switch for the public website.
 *
 *   const { t, lang, setLang } = useLang();
 *   <Typography>{t('hero.title')}</Typography>
 *
 * Missing Urdu text falls back to English. Urdu blocks get lang="ur" + dir="rtl" (Nastaliq font, theme.js).
 * To add a language: add a column to TEXT.
 */
import { createContext, useContext, useMemo, useState } from 'react';
import { storage } from './api';

const TEXT = {
  'nav.home': ['Home', 'ہوم'],
  'nav.advisor': ['AI advisor', 'اے آئی مشیر'],
  'nav.calculator': ['Calculator', 'کیلکولیٹر'],
  'nav.backup': ['Backup planner', 'بیک اپ پلانر'],
  'nav.survey': ['Free site survey', 'مفت سائٹ سروے'],
  'nav.staff': ['Staff login', 'اسٹاف لاگ ان'],
  'nav.talk': ['Talk to the advisor', 'مشیر سے بات کریں'],

  'hero.title': ['Solar sized for your bill and your load-shedding.',
    'آپ کے بل اور لوڈشیڈنگ کے مطابق سولر۔'],
  'hero.body': ['Upload your electricity bill or just talk. SolarSaathi works out the right system, the price, your new bill and how many years it takes to pay for itself - with the 2026 net-billing rules.',
    'اپنا بجلی کا بل اپلوڈ کریں یا بس بات کریں۔ سولر ساتھی صحیح سسٹم، قیمت، نیا بل اور کتنے سال میں پیسے پورے ہوں گے، سب بتاتا ہے — 2026 کے نیٹ بلنگ قوانین کے ساتھ۔'],
  'hero.start': ['Start with my bill', 'میرے بل سے شروع کریں'],
  'hero.calc': ['Use the calculator', 'کیلکولیٹر استعمال کریں'],
  'strip.title': ['When does your light go?', 'آپ کی بجلی کب جاتی ہے؟'],
  'strip.sun': ['Panels working', 'پینل کام کر رہے ہیں'],
  'strip.cut': ['Load-shedding', 'لوڈشیڈنگ'],
  'strip.ongrid': ['On-grid', 'آن گرڈ'],
  'strip.hybrid': ['Hybrid', 'ہائبرڈ'],
  'strip.off': ['switches off during this cut', 'اس دوران بند ہو جاتا ہے'],
  'strip.on_sun': ['runs your house from the panels', 'پینلز سے گھر چلاتا ہے'],
  'strip.on_batt': ['runs your house from the battery', 'بیٹری سے گھر چلاتا ہے'],
  'strip.on_both': ['runs from panels, then battery', 'پہلے پینل، پھر بیٹری سے چلتا ہے'],

  'ways.title': ['Three ways to get your answer', 'جواب حاصل کرنے کے تین طریقے'],
  'ways.chat.t': ['Chat or speak with the AI advisor', 'اے آئی مشیر سے لکھ کر یا بول کر بات کریں'],
  'ways.chat.b': ['English, Roman Urdu or Urdu. Snap your bill - it reads 12 months of units, and you check them before anything is calculated.',
    'انگریزی، رومن اردو یا اردو۔ بل کی تصویر لیں — یہ 12 مہینوں کے یونٹ پڑھتا ہے، اور حساب سے پہلے آپ خود چیک کرتے ہیں۔'],
  'ways.calc.t': ['Fill in the calculator', 'کیلکولیٹر بھریں'],
  'ways.calc.b': ['Prefer forms? Units, city, load-shedding times and what you want with WAPDA. Works even when the AI is busy.',
    'فارم پسند ہیں؟ یونٹ، شہر، لوڈشیڈنگ کا وقت اور واپڈا کے بارے میں آپ کی پسند۔ اے آئی مصروف ہو تب بھی چلتا ہے۔'],
  'ways.backup.t': ['Plan your backup', 'اپنا بیک اپ پلان کریں'],
  'ways.backup.b': ['Tick your fans, lights, fridge and motor and see which battery keeps them running, and for how long.',
    'پنکھے، لائٹیں، فریج اور موٹر منتخب کریں اور دیکھیں کون سی بیٹری انہیں کتنی دیر چلائے گی۔'],

  'wapda.title': ['Stay with WAPDA, or leave it?', 'واپڈا کے ساتھ رہیں یا چھوڑ دیں؟'],
  'wapda.body': ['Every quotation shows your monthly bill for each choice, so you can decide with real numbers.',
    'ہر کوٹیشن میں ہر انتخاب کا ماہانہ بل دکھایا جاتا ہے، تاکہ آپ اصل نمبروں سے فیصلہ کریں۔'],
  'wapda.net.t': ['Net billing (green meter)', 'نیٹ بلنگ (گرین میٹر)'],
  'wapda.net.b': ['Extra units go to WAPDA for about Rs 11 each. Lowest bill when you have a big system.',
    'زائد یونٹ تقریباً 11 روپے فی یونٹ واپڈا کو جاتے ہیں۔ بڑے سسٹم کے ساتھ سب سے کم بل۔'],
  'wapda.noexp.t': ['Connected, no green meter', 'کنکشن، مگر گرین میٹر نہیں'],
  'wapda.noexp.b': ['No paperwork with the DISCO. Solar runs the house in the day, WAPDA at night. Extra solar is not sold.',
    'ڈسکو کے ساتھ کوئی کاغذی کارروائی نہیں۔ دن میں سولر، رات کو واپڈا۔ زائد بجلی فروخت نہیں ہوتی۔'],
  'wapda.off.t': ['Fully off-grid', 'مکمل آف گرڈ'],
  'wapda.off.b': ['No bill at all. Needs more panels and a bigger battery for winter fog - we show which months may fall short.',
    'کوئی بل نہیں۔ سردیوں کی دھند کے لیے زیادہ پینل اور بڑی بیٹری چاہیے — ہم بتاتے ہیں کن مہینوں میں کمی ہو سکتی ہے۔'],

  'trust.title': ['Where the numbers come from', 'نمبر کہاں سے آتے ہیں'],
  'trust.ai': ['The AI only understands your words and reads your bill. Every size, price and saving comes from a fixed calculator that gives the same answer every time.',
    'اے آئی صرف آپ کی بات سمجھتا اور بل پڑھتا ہے۔ ہر سائز، قیمت اور بچت ایک مقررہ کیلکولیٹر سے آتی ہے جو ہر بار ایک ہی جواب دیتا ہے۔'],
  'trust.sun': ['Sunlight from NASA satellite records for your location, not a guess.',
    'دھوپ کا ڈیٹا آپ کے مقام کے لیے ناسا سیٹلائٹ ریکارڈ سے، اندازہ نہیں۔'],
  'trust.tariff': ['Bills from the NEPRA domestic tariff (Feb 2026) and the net-billing rules for new solar users.',
    'بل نیپرا ڈومیسٹک ٹیرف (فروری 2026) اور نئے سولر صارفین کے نیٹ بلنگ قوانین کے مطابق۔'],
  'trust.price': ['Prices set by the installer and shown item by item.', 'قیمتیں انسٹالر طے کرتا ہے اور ہر چیز الگ دکھائی جاتی ہے۔'],

  'faq.title': ['Questions people ask', 'اکثر پوچھے جانے والے سوال'],

  'calc.title': ['Solar calculator', 'سولر کیلکولیٹر'],
  'calc.sub': ['No AI needed. Same calculator the advisor uses.', 'اے آئی کی ضرورت نہیں۔ وہی کیلکولیٹر جو مشیر استعمال کرتا ہے۔'],
  'calc.units': ['Monthly units', 'ماہانہ یونٹ'],
  'calc.city': ['City', 'شہر'],
  'calc.go': ['Calculate my options', 'میرے آپشن نکالیں'],
  'out.none': ['No load-shedding', 'لوڈشیڈنگ نہیں'],
  'out.daily': ['Every day', 'روزانہ'],
  'out.some': ['Some days a week', 'ہفتے میں کچھ دن'],
  'out.days': ['Days a week', 'ہفتے میں دن'],
  'out.time': ['From - to', 'کب سے کب تک'],
  'out.unknown': ['I don\'t know the time', 'وقت معلوم نہیں'],
  'out.hours': ['Hours each time', 'ہر بار کتنے گھنٹے'],
  'grid.title': ['What do you want with WAPDA?', 'واپڈا کے ساتھ کیا چاہتے ہیں؟'],
  'grid.auto': ['Show me what is best', 'بہترین بتائیں'],
  'grid.net': ['Net billing (green meter)', 'نیٹ بلنگ'],
  'grid.noexp': ['Stay connected, no green meter', 'کنکشن رکھیں، گرین میٹر نہیں'],
  'grid.off': ['Leave WAPDA completely', 'واپڈا مکمل چھوڑ دیں'],
  'grid.none': ['I have no WAPDA connection', 'میرے پاس واپڈا کنکشن نہیں'],

  'backup.title': ['Backup planner', 'بیک اپ پلانر'],
  'backup.sub': ['What must keep running when the light goes?', 'بجلی جانے پر کیا چلتا رہنا چاہیے؟'],
  'backup.hours': ['Longest cut (hours)', 'سب سے لمبی لوڈشیڈنگ (گھنٹے)'],

  'survey.title': ['Book a free site survey', 'مفت سائٹ سروے بک کریں'],
  'survey.sub': ['An engineer checks your roof, shade and wiring, then confirms the final price. No charge.',
    'انجینئر آپ کی چھت، سایہ اور وائرنگ چیک کر کے حتمی قیمت بتاتا ہے۔ کوئی فیس نہیں۔'],
};

const LangContext = createContext(null);

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(storage.get('ss_lang', localStorage) || 'en');
  const value = useMemo(() => ({
    lang,
    ur: lang === 'ur',
    setLang: (next) => { storage.set('ss_lang', next, localStorage); setLangState(next); },
    t: (key) => {
      const row = TEXT[key];
      if (!row) return key;
      return (lang === 'ur' && row[1]) || row[0];
    },
    /** props for a block of text: Urdu gets the right font and direction */
    dir: lang === 'ur' ? { lang: 'ur', dir: 'rtl' } : { lang: 'en' },
  }), [lang]);
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export const useLang = () => useContext(LangContext);
