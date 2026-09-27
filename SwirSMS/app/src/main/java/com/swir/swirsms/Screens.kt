package com.swir.swirsms

import android.Manifest
import android.content.Context
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalLayoutApi::class)
@Composable fun HistoryScreen(w: Words,messages: List<Message>,onCancel:(String)->Unit,onLoad:(Message)->Unit,onDelete:(String)->Unit) {
    var query by remember { mutableStateOf("") }
    var filter by remember { mutableIntStateOf(0) }
    var selected by remember { mutableStateOf<Message?>(null) }
    val shown=messages.filter { m -> (query.isBlank() || (m.number+" "+m.name+" "+m.body).contains(query,true)) && when(filter) {1->m.state=="QUEUED";2->m.state in listOf("FAILED","PARTIAL","UNKNOWN","DELIVERY_FAILED","EXPIRED");else->true} }
    LazyColumn(Modifier.widthIn(max=720.dp).fillMaxSize().testTag("history"),contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        item { Text(w.t("Historia wysyłek","Send history"),style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold) }
        item { Text(w.t("Ostatnie 300 pozycji wysłanych z SwirSMS. Odpowiedzi odbierzesz w domyślnej aplikacji SMS telefonu.","Last 300 entries sent from SwirSMS. Replies arrive in your phone's default SMS app."),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant) }
        item { OutlinedTextField(query,{query=it},singleLine=true,label={Text(w.t("Szukaj numeru, osoby lub treści","Search number, person or message"))},modifier=Modifier.fillMaxWidth()) }
        item { FlowRow(horizontalArrangement=Arrangement.spacedBy(8.dp)) { listOf(w.t("Wszystkie","All"),w.t("Kolejka","Queue"),w.t("Do sprawdzenia","Check status")).forEachIndexed { i,s -> FilterChip(selected=filter==i,onClick={filter=i},label={Text(s)}) } } }
        if(shown.isEmpty()) item { Panel(w.t("Brak wiadomości","No messages")) { Text(w.t("Tutaj pojawią się rzeczywiste wysyłki oraz zaplanowane SMS-y.","Actual sends and scheduled SMS will appear here.")) } }
        items(shown,key={it.id}) { m ->
            Card(onClick={selected=m},colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface)) {
                Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
                    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                        Text(m.name.ifBlank { m.number },Modifier.weight(1f),fontWeight=FontWeight.SemiBold)
                        Text(w.state(m.state),style=MaterialTheme.typography.labelMedium,color=if(m.state in listOf("FAILED","PARTIAL","UNKNOWN","DELIVERY_FAILED")) MaterialTheme.colorScheme.error else Blue)
                    }
                    if(m.name.isNotBlank()) Text(m.number,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(m.body,maxLines=3,style=MaterialTheme.typography.bodyMedium)
                    Text(m.simLabel+" · "+dateText(if(m.state=="QUEUED") m.due else m.created),style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                    if(m.state=="SENT") Text(if(m.reports) w.t("Wysłano, oczekiwanie na raport dostarczenia.","Sent; waiting for a delivery report.") else w.t("Nie żądano raportu dostarczenia.","No delivery report requested."),style=MaterialTheme.typography.bodySmall)
                    if(m.state=="UNKNOWN") Text(w.detail(m.detail),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.error)
                }
            }
        }
    }
    selected?.let { initial ->
        val m=messages.firstOrNull { it.id==initial.id } ?: initial
        AlertDialog(onDismissRequest={selected=null},title={Text(w.state(m.state))},text={Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Text(m.name+"\n"+m.number); Text(m.simLabel); Text(dateText(m.due)); Text(m.body)
            if(m.parts>0) Text("${m.parts} "+w.t("części SMS","SMS segments"))
            if(m.detail.isNotBlank()) Text(w.detail(m.detail),color=MaterialTheme.colorScheme.error)
            if(m.state=="SENT") Text(w.t("Brak raportu nie oznacza błędu ani potwierdzonego dostarczenia. Sieć lub telefon odbiorcy mogą nie obsługiwać raportów.","No report means neither failure nor confirmed delivery. The network or recipient's phone may not support reports."))
            if(m.state=="QUEUED") OutlinedButton(onClick={onCancel(m.id);selected=null},modifier=Modifier.fillMaxWidth()) { Text(w.t("Anuluj zaplanowany SMS","Cancel scheduled SMS")) }
            OutlinedButton(onClick={onLoad(m);selected=null},modifier=Modifier.fillMaxWidth()) { Text(w.t("Wczytaj do edytora","Load into editor")) }
            if(m.state !in listOf("QUEUED","SENDING","UNKNOWN")) TextButton(onClick={onDelete(m.id);selected=null}) { Text(w.t("Usuń wpis z historii","Delete history entry")) }
        }},confirmButton={TextButton(onClick={selected=null}) { Text(w.t("Zamknij","Close")) }})
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable fun LibraryScreen(w: Words,library: List<SavedItem>,people: List<Recipient>,body: String,onEdit:(SavedItem)->Unit,onUse:(SavedItem)->Unit,onDelete:(String)->Unit) {
    var pendingDelete by remember { mutableStateOf<SavedItem?>(null) }
    LazyColumn(Modifier.widthIn(max=720.dp).fillMaxSize().testTag("library"),contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        item { Text(w.t("Twoja biblioteka","Your library"),style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold) }
        item { Text(w.t("Ulubione, grupy i szablony są zapisane wyłącznie w telefonie.","Favourites, groups and templates are stored only on this phone."),style=MaterialTheme.typography.bodyMedium) }
        item { FlowRow(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
            AssistChip(onClick={onEdit(SavedItem(kind="CONTACT",title=""))},label={Text(w.t("+ Ulubiony","+ Favourite"))})
            AssistChip(onClick={onEdit(SavedItem(kind="GROUP",title="",people=people))},label={Text(w.t("+ Grupa","+ Group"))})
            AssistChip(onClick={onEdit(SavedItem(kind="TEMPLATE",title="",body=body))},label={Text(w.t("+ Szablon","+ Template"))})
        } }
        if(library.isEmpty()) item { Panel(w.t("Zacznij od swoich skrótów","Save your shortcuts")) { Text(w.t("Utwórz grupę z odbiorców zaznaczonych w edytorze, zapisz treść jako szablon albo dodaj ulubiony numer.","Create a group from recipients selected in the editor, save your message as a template, or add a favourite number.")) } }
        items(library,key={it.id}) { item -> Panel(item.title,when(item.kind) {"CONTACT"->w.t("Ulubiony kontakt","Favourite contact");"GROUP"->w.t("Grupa","Group")+" · ${item.people.size}";else->w.t("Szablon","Template")}) {
            Text(if(item.kind=="TEMPLATE") item.body else item.people.joinToString("\n") { it.name.ifBlank { it.number } },maxLines=4,style=MaterialTheme.typography.bodyMedium)
            FlowRow(horizontalArrangement=Arrangement.spacedBy(4.dp)) {
                TextButton(onClick={onUse(item)}) { Text(w.t("Użyj","Use")) }
                TextButton(onClick={onEdit(item)}) { Text(w.t("Edytuj","Edit")) }
                TextButton(onClick={pendingDelete=item}) { Text(w.t("Usuń","Delete")) }
            }
        } }
    }
    pendingDelete?.let { item -> AlertDialog(onDismissRequest={pendingDelete=null},title={Text(w.t("Usunąć pozycję?","Delete item?"))},text={Text(item.title)},confirmButton={TextButton(onClick={onDelete(item.id);pendingDelete=null}) {Text(w.t("Usuń","Delete"))}},dismissButton={TextButton(onClick={pendingDelete=null}) {Text(w.t("Anuluj","Cancel"))}}) }
}

@Composable fun SavedEditor(w: Words,item: SavedItem,onDismiss:()->Unit,onSave:(SavedItem)->Unit) {
    var title by remember(item.id) { mutableStateOf(item.title) }
    var content by remember(item.id) { mutableStateOf(if(item.kind=="TEMPLATE") item.body else item.people.joinToString("\n") {it.number}) }
    var invalid by remember { mutableStateOf(false) }
    AlertDialog(onDismissRequest=onDismiss,title={Text(w.t("Zapisz w bibliotece","Save to library"))},text={Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        OutlinedTextField(title,{title=it.take(80)},label={Text(w.t("Nazwa","Name"))},singleLine=true,isError=invalid && title.isBlank(),modifier=Modifier.fillMaxWidth())
        OutlinedTextField(content,{content=it.take(if(item.kind=="TEMPLATE")1530 else 500)},label={Text(if(item.kind=="TEMPLATE") w.t("Treść szablonu","Template text") else w.t("Numery — po jednym w wierszu","Numbers — one per line"))},minLines=if(item.kind=="CONTACT")1 else 4,maxLines=8,modifier=Modifier.fillMaxWidth(),isError=invalid)
        if(invalid) Text(w.t("Wpisz nazwę i poprawną treść. Grupa: 1–20 numerów; ulubiony: jeden numer.","Enter a name and valid content. Group: 1–20 numbers; favourite: one number."),color=MaterialTheme.colorScheme.error)
    }},confirmButton={TextButton(onClick={
        if(title.isBlank() || content.isBlank()) {invalid=true;return@TextButton}
        if(item.kind=="TEMPLATE") onSave(item.copy(title=title.trim(),body=content))
        else {
            val numbers=content.split(Regex("[\n,;]")).map {it.trim()}.filter {it.isNotBlank()}
            val normalized=numbers.map {PhoneRules.normalize(it)}
            if(normalized.any {it==null} || normalized.distinct().size !in 1..20 || (item.kind=="CONTACT" && normalized.size!=1)) invalid=true
            else onSave(item.copy(title=title.trim(),people=normalized.filterNotNull().distinct().map { n -> item.people.firstOrNull {it.number==n} ?: Recipient(if(item.kind=="CONTACT")title.trim() else "",n) }))
        }
    }) {Text(w.t("Zapisz","Save"))}},dismissButton={TextButton(onClick=onDismiss) {Text(w.t("Anuluj","Cancel"))}})
}

@OptIn(ExperimentalLayoutApi::class)
@Composable fun SettingsScreen(w: Words,language: String,reports: Boolean,lock: Boolean,permissionRevision: Int,context: Context,onLanguage:(String)->Unit,onReports:(Boolean)->Unit,onLock:(Boolean)->Unit,onPermissions:()->Unit,onClear:()->Unit) {
    val permissions=remember(permissionRevision) { Sims.permission(context,Manifest.permission.SEND_SMS) to Sims.permission(context,Manifest.permission.READ_PHONE_STATE) }
    Column(Modifier.widthIn(max=720.dp).fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp).testTag("settings"),verticalArrangement=Arrangement.spacedBy(16.dp)) {
        Text(w.t("Ustawienia","Settings"),style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold)
        Panel(w.t("Wysyłanie i prywatność","Sending & privacy")) {
            Row(verticalAlignment=Alignment.CenterVertically) { Column(Modifier.weight(1f)) { Text(w.t("Raporty dostarczenia","Delivery reports")); Text(w.t("Dla nowych wiadomości; zależą od sieci.","For new messages; network dependent."),style=MaterialTheme.typography.bodySmall) }; Switch(checked=reports,onCheckedChange=onReports) }
            HorizontalDivider()
            Row(verticalAlignment=Alignment.CenterVertically) { Column(Modifier.weight(1f)) { Text(w.t("Blokada aplikacji","App lock")); Text(w.t("Biometria lub kod blokady telefonu.","Biometrics or device screen-lock credential."),style=MaterialTheme.typography.bodySmall) }; Switch(checked=lock,onCheckedChange=onLock) }
            Text(w.t("Po włączeniu blokady treści są ukrywane po opuszczeniu aplikacji, a zrzuty ekranu blokowane. Wcześniej zatwierdzone zaplanowane SMS-y nadal mogą się wysłać.","With app lock enabled, content is hidden when you leave and screenshots are blocked. Previously approved scheduled SMS may still be sent."),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Panel(w.t("Język","Language")) { FlowRow(horizontalArrangement=Arrangement.spacedBy(8.dp)) { listOf("system" to w.t("Systemowy","System"),"pl" to "Polski","en" to "English").forEach { (code,label) -> FilterChip(selected=language==code,onClick={onLanguage(code)},label={Text(label)}) } }; Text(w.t("Automatycznie: polski dla systemu PL, w innych językach angielski.","Automatic: Polish on a Polish system, otherwise English."),style=MaterialTheme.typography.bodySmall) }
        Panel(w.t("Uprawnienia","Permissions")) {
            Text("SMS: "+if(permissions.first) w.t("udzielono","allowed") else w.t("brak","not allowed"))
            Text("SIM: "+if(permissions.second) w.t("udzielono","allowed") else w.t("brak","not allowed"))
            OutlinedButton(onClick=onPermissions) {Text(w.t("Przyznaj uprawnienia","Grant permissions"))}
            Text(w.t("Po trwałej odmowie włącz uprawnienia w systemowych ustawieniach aplikacji SwirSMS. Kontakty wybierasz pojedynczo — aplikacja nie odczytuje całej książki.","After a permanent denial, enable permissions in Android's SwirSMS app settings. Contacts are picked individually; the app does not read your entire address book."),style=MaterialTheme.typography.bodySmall)
        }
        Panel(w.t("Dane lokalne","Local data")) {
            Text(w.t("Bez uprawnienia INTERNET, reklam, analityki, konta i konfiguracji API. Kopie w chmurze oraz przenoszenie danych aplikacji są wyłączone.","No INTERNET permission, ads, analytics, account or API configuration. Cloud backup and app-data transfer are disabled."))
            Text(w.t("Historia, szablony i wersja robocza są w prywatnych danych aplikacji. Odinstalowanie usuwa je. Zwykły SMS nie jest szyfrowany end-to-end.","History, templates and draft are in private app data. Uninstalling removes them. Standard SMS is not end-to-end encrypted."),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            OutlinedButton(onClick=onClear) {Text(w.t("Wyczyść zakończoną historię","Clear completed history"))}
        }
        Panel("SwirSMS · ${BuildConfig.VERSION_NAME}","by Swir") {
            Text(w.t("To aplikacja do wysyłania zwykłych SMS-ów z SIM, nie zamiennik systemowej skrzynki odbiorczej. Nie ma trybu DEMO.","A real SIM-based standard SMS sender, not a replacement for the system inbox. There is no DEMO mode."))
            Text(w.t("Nazwa zamiast numeru i Flash / Class 0 nie są dostępne w tej samodzielnej wersji. Nie ma ukrytej bramki ani udawanych przełączników.","Alphanumeric sender names and Flash / Class 0 are not available in this standalone version. There is no hidden gateway or simulated switch."),style=MaterialTheme.typography.bodySmall)
            Text(w.t("Harmonogram: Android może opóźnić zadanie przez oszczędzanie baterii, wymuszone zatrzymanie lub restart. Po ponownym uruchomieniu telefonu najpierw go odblokuj. Opóźnienie >24 h kończy wiadomość statusem Wygasła. Brak zasięgu nie uruchamia automatycznej ponownej wysyłki.","Scheduling: Android may delay work because of battery saving, force-stop or reboot. Unlock the phone after restarting it. Delays >24 h expire the message. No service does not trigger automatic resending."),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
