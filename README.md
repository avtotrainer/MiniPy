# 🐍 MiniPy
**მსუბუქი ინტერაქტიული Python გარემო**
*განკუთვნილია სწავლების დასაწყისისთვის, აწყობილია PySide6 და qtconsole ბიბლიოთეკებზე.*

---

## 🎯 მიზანი
**MiniPy** არის პატარა, პლატფორმათაშორისი აპლიკაცია, რომელიც აერთიანებს ტექსტურ რედაქტორსა და ჩაშენებულ Python REPL-ს (IPython-ზე დაფუძნებულს).
ის საშუალებას აძლევს მოსწავლეებს და დამწყებთ, მარტივად დაწერონ და გააშვონ Python კოდი — უფრო ინტერაქტიულად, ვიდრე IDLE, მაგრამ გაცილებით მარტივად, ვიდრე VS Code.

---

## 💻 მხარდაჭერილი პლატფორმები
- **Manjaro Linux** (Hyprland, GNOME, XFCE)
- **Windows 10/11**
- სხვა **Linux დესკტოპები** (Wayland და X11 გარემოები)

---

## 🧩 ძირითადი მახასიათებლები
- ზედა **ტექსტური რედაქტორი** (`QPlainTextEdit`)
- ქვედა **REPL ფანჯარა** (IPython/qtconsole)
- ღილაკები:
  - 🗂️ **Open** — ფაილის გახსნა
  - 💾 **Save** — ფაილის შენახვა
  - ▶️ **Run** — სკრიპტის გაშვება REPL-ში
  - 🧹 **Clear** — REPL-ის გასუფთავება
- იყენებს **სისტემურ Python 3.12–3.13+ ინტერპრეტატორს**
- მუშაობს როგორც **Wayland**, ასევე **X11** და **Windows** გარემოებში
- სრულიად **პორტაბელურია** (PyInstaller ან AppImage ფორმატით)

---

## 🚀 ინსტალაცია და გაშვება

### დამოკიდებულებები
```bash
sudo pacman -S python-pip python-jupyter_client python-ipykernel qt6-base
pip install --user PySide6 qtconsole
```
## 📦 პაკეტები და ინსტალაცია
ყველა გარე მოდული დაყენდეს სისტემურ Python-ში:

```bash
# 🔹 Manjaro / Linux

# აუცილებელი ძირითადი პაკეტები
```bash 
sudo pacman -Syu python-ipykernel python-jupyter_client python-qtconsole
```
# PySide6 არის AUR პაკეტი — დააყენე yay-ის მეშვეობით
```bash
sudo pacman -S base-devel git yay   # თუ ჯერ არ გაქვს
yay -S pyside6
```
# შემოწმება
```bash
python3 -c "import PySide6, qtconsole, jupyter_client, ipykernel; print('OK')"
```
# Windows
```powershell

py -m pip install PySide6 ipykernel jupyter_client
```
