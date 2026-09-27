package com.swir.swirsms

import android.Manifest
import android.app.DatePickerDialog
import android.app.TimePickerDialog
import android.content.Intent
import android.provider.ContactsContract.CommonDataKinds.Phone
import android.text.format.DateFormat
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.Calendar

data class SendPlan(val people: List<Recipient>,val body: String,val sim: SimChoice,val due: Long,val reports: Boolean,val parts: Int)

@OptIn(ExperimentalMaterial3Api::class,ExperimentalLayoutApi::class)
@Composable fun SwirSmsApp(activity: MainActivity) {
    val context=activity.applicationContext
    val prefs=remember { LocalPrefs(context) }
    val db=remember { SmsDb.get(context) }
    val scope=rememberCoroutineScope()
    val snack=remember { SnackbarHostState() }
    var lang by remember { mutableStateOf(prefs.lang) }
    val w=remember(lang) { Words(lang) }
    var tab by remember { mutableIntStateOf(0) }
    var people by remember { mutableStateOf(prefs.draftPeople) }
    var body by remember { mutableStateOf(prefs.draft) }
    var number by remember { mutableStateOf("") }
    var sims by remember { mutableStateOf(Sims.list(context)) }
    var selected by remember { mutableStateOf<SimChoice?>(null) }
    var reports by remember { mutableStateOf(prefs.reports) }
    var lock by remember { mutableStateOf(prefs.lock) }
    var permissionRevision by remember { mutableIntStateOf(0) }
    var busy by remember { mutableStateOf(false) }
    var plan by remember { mutableStateOf<SendPlan?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var simMenu by remember { mutableStateOf(false) }
    var chooseSaved by remember { mutableStateOf<String?>(null) }
    var edit by remember { mutableStateOf<SavedItem?>(null) }
    var clearHistory by remember { mutableStateOf(false) }
    val history by produceState(initialValue=emptyList<Message>(),db) { db.revision.collectLatest { value=withContext(Dispatchers.IO) { db.messages() } } }
    val library by produceState(initialValue=emptyList<SavedItem>(),db) { db.revision.collectLatest { value=withContext(Dispatchers.IO) { db.saved() } } }
    fun notify(text: String) { scope.launch { snack.showSnackbar(text) } }
    fun replacePeople(items: List<Recipient>) { people=items; prefs.draftPeople=items }
    fun replaceBody(text: String) { body=text.take(1530); prefs.draft=body }
    fun addPeople(items: List<Recipient>) {
        if(items.any { PhoneRules.normalize(it.number)==null }) { error=w.t("Sprawdź numer: użyj cyfr i kodu kraju, np. +47… lub +48…", "Check the number: use digits and preferably a country code, e.g. +47… or +48…"); return }
        val all=PhoneRules.unique(people+items)
        if(all.size>20) { error=w.t("Maksymalnie 20 odbiorców w jednej wysyłce.","Maximum 20 recipients per send."); return }
        replacePeople(all)
    }
    val permissions=rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        sims=Sims.list(context); permissionRevision++
        notify(w.t("Uprawnienia odświeżone. Sprawdź SIM i ponownie naciśnij wysyłanie.","Permissions refreshed. Check the SIM and press send again."))
    }
    val contactPicker=rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val uri=result.data?.data
        if(result.resultCode==android.app.Activity.RESULT_OK && uri!=null) scope.launch {
            val contact=withContext(Dispatchers.IO) { runCatching {
                activity.contentResolver.query(uri,arrayOf(Phone.DISPLAY_NAME,Phone.NUMBER),null,null,null)?.use { c ->
                    if(c.moveToFirst()) Recipient(c.getString(0).orEmpty(),c.getString(1).orEmpty()) else null
                }
            }.getOrNull() }
            if(contact!=null) addPeople(listOf(contact)) else error=w.t("Nie udało się odczytać wybranego numeru. Wpisz go ręcznie.","Could not read the selected number. Enter it manually.")
        }
    }
    DisposableEffect(activity) {
        val observer=LifecycleEventObserver { _, event -> if(event==Lifecycle.Event.ON_RESUME) { sims=Sims.list(context); permissionRevision++ } }
        activity.lifecycle.addObserver(observer)
        onDispose { activity.lifecycle.removeObserver(observer) }
    }
    LaunchedEffect(sims) {
        selected=sims.firstOrNull { it.id==prefs.selectedSim } ?: if(prefs.selectedSim==-1 && sims.size==1) sims.single() else null
        selected?.let { prefs.selectedSim=it.id }
    }
    fun requestPermissions() { permissions.launch(arrayOf(Manifest.permission.SEND_SMS,Manifest.permission.READ_PHONE_STATE)) }
    fun review(due: Long) {
        if(busy) return
        if(people.isEmpty() || body.isBlank()) { error=w.t("Dodaj odbiorcę i wpisz wiadomość.","Add a recipient and write a message."); return }
        if(!Sims.hasSms(context)) { error=w.t("To urządzenie nie ma obsługi SMS przez SIM.","This device does not support SMS via SIM."); return }
        if(!Sims.permission(context,Manifest.permission.SEND_SMS) || !Sims.permission(context,Manifest.permission.READ_PHONE_STATE)) { requestPermissions(); return }
        val sim=selected
        if(sim==null || Sims.list(context).none { it.id==sim.id }) { error=w.t("Wybierz aktywną kartę SIM. Nie przełączam kart automatycznie.","Choose an active SIM. SIM cards are never switched silently."); sims=Sims.list(context); return }
        val segments=runCatching { Sims.manager(context,sim.id).divideMessage(body).size }.getOrDefault(0)
        if(segments !in 1..10) { error=w.t("Wiadomość musi zmieścić się w maksymalnie 10 częściach SMS.","The message must fit in no more than 10 SMS segments."); return }
        plan=SendPlan(people.toList(),body,sim,due,reports,segments)
    }
    fun schedulePicker() {
        val c=Calendar.getInstance().apply { add(Calendar.HOUR_OF_DAY,1) }
        val datePicker=DatePickerDialog(activity,{_,year,month,day ->
            c.set(Calendar.YEAR,year); c.set(Calendar.MONTH,month); c.set(Calendar.DAY_OF_MONTH,day)
            TimePickerDialog(activity,{_,hour,minute ->
                c.set(Calendar.HOUR_OF_DAY,hour); c.set(Calendar.MINUTE,minute); c.set(Calendar.SECOND,0); c.set(Calendar.MILLISECOND,0)
                if(c.timeInMillis<=System.currentTimeMillis()+30_000) error=w.t("Wybierz przyszły termin, co najmniej minutę od teraz.","Choose a future time, at least one minute from now.") else review(c.timeInMillis)
            },c.get(Calendar.HOUR_OF_DAY),c.get(Calendar.MINUTE),DateFormat.is24HourFormat(activity)).show()
        },c.get(Calendar.YEAR),c.get(Calendar.MONTH),c.get(Calendar.DAY_OF_MONTH))
        datePicker.datePicker.minDate=System.currentTimeMillis(); datePicker.show()
    }
    MaterialTheme(colorScheme=SwirColors) {
        if(lock && !activity.unlocked) {
            Surface(modifier=Modifier.fillMaxSize(),color=Ink) {
                Column(Modifier.fillMaxSize().safeDrawingPadding().padding(32.dp),verticalArrangement=Arrangement.Center,horizontalAlignment=Alignment.CenterHorizontally) {
                    Icon(Icons.Rounded.Lock,null,Modifier.size(56.dp),tint=Blue)
                    Spacer(Modifier.height(20.dp)); Text("SwirSMS",style=MaterialTheme.typography.headlineLarge)
                    Text(w.t("Twoje wiadomości są ukryte.","Your messages are hidden."),Modifier.padding(vertical=16.dp))
                    Button(onClick={ activity.authenticate("SwirSMS") { success,msg -> if(!success) error=w.detail(msg) } }) { Text(w.t("Odblokuj", "Unlock")) }
                    if(error!=null) Text(error!!,Modifier.padding(top=16.dp),color=MaterialTheme.colorScheme.error)
                }
            }
            return@MaterialTheme
        }
        Scaffold(containerColor=Ink,snackbarHost={ SnackbarHost(snack) },topBar={
            TopAppBar(title={ Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                Icon(Icons.Rounded.Sms,null,tint=Blue)
                Column { Text("SwirSMS",fontWeight=FontWeight.Bold); Text("STANDALONE · SIM",style=MaterialTheme.typography.labelSmall,color=Blue) }
            } },actions={ AssistChip(onClick={tab=3},label={Text(w.t("Lokalnie", "Local"))},leadingIcon={Icon(Icons.Rounded.Shield,null,Modifier.size(16.dp))}); Spacer(Modifier.width(12.dp)) },colors=TopAppBarDefaults.topAppBarColors(containerColor=Ink))
        },bottomBar={
            NavigationBar(containerColor=MaterialTheme.colorScheme.surface) {
                val labels=listOf(w.t("Wiadomość","Compose"),w.t("Historia","History"),w.t("Biblioteka","Library"),w.t("Ustawienia","Settings"))
                val icons=listOf(Icons.Rounded.Edit,Icons.Rounded.History,Icons.Rounded.Bookmarks,Icons.Rounded.Settings)
                labels.forEachIndexed { i,label -> NavigationBarItem(selected=tab==i,onClick={tab=i},icon={Icon(icons[i],label)},label={Text(label)},modifier=Modifier.testTag("nav-$i")) }
            }
        }) { padding ->
            Box(Modifier.fillMaxSize().padding(padding).imePadding(),contentAlignment=Alignment.TopCenter) {
                when(tab) {
                    0 -> Column(Modifier.widthIn(max=720.dp).fillMaxWidth().verticalScroll(rememberScrollState()).padding(16.dp).testTag("composer"),verticalArrangement=Arrangement.spacedBy(16.dp)) {
                        Hero(w)
                        Panel(w.t("Odbiorcy", "Recipients")+" · ${people.size}/20",w.t("Wybierasz wyłącznie wskazane numery. Każdy odbiorca dostaje osobny SMS.","Only selected numbers are used. Each recipient receives a separate SMS.")) {
                            Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                                OutlinedButton(onClick={ runCatching { contactPicker.launch(Intent(Intent.ACTION_PICK,Phone.CONTENT_URI)) }.onFailure { error=w.t("Brak aplikacji kontaktów. Wpisz numer ręcznie.","No contacts app available. Enter the number manually.") } },modifier=Modifier.weight(1f)) { Icon(Icons.Rounded.Contacts,null,Modifier.size(18.dp)); Spacer(Modifier.width(6.dp)); Text(w.t("Kontakty","Contacts")) }
                                OutlinedButton(onClick={chooseSaved="GROUP"},modifier=Modifier.weight(1f)) { Icon(Icons.Rounded.Groups,null,Modifier.size(18.dp)); Spacer(Modifier.width(6.dp)); Text(w.t("Grupy","Groups")) }
                            }
                            Row(verticalAlignment=Alignment.CenterVertically) {
                                OutlinedTextField(value=number,onValueChange={number=it.take(60)},label={Text(w.t("Numer telefonu","Phone number"))},placeholder={Text("+47 … / +48 …")},singleLine=true,keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Phone),modifier=Modifier.weight(1f).testTag("manual-number"))
                                IconButton(onClick={addPeople(listOf(Recipient("",number))); if(PhoneRules.normalize(number)!=null) number=""},modifier=Modifier.testTag("add-number")) { Icon(Icons.Rounded.Add,w.t("Dodaj numer","Add number"),tint=Blue) }
                            }
                            if(library.any { it.kind=="CONTACT" }) TextButton(onClick={chooseSaved="CONTACT"}) { Icon(Icons.Rounded.Star,null,Modifier.size(18.dp)); Text(w.t(" Wybierz z ulubionych"," Choose from favourites")) }
                            people.forEach { p ->
                                Row(verticalAlignment=Alignment.CenterVertically,modifier=Modifier.fillMaxWidth()) {
                                    Checkbox(checked=true,onCheckedChange={replacePeople(people.filterNot { it.number==p.number })})
                                    Column(Modifier.weight(1f)) { Text(p.name.ifBlank { p.number },style=MaterialTheme.typography.bodyMedium); if(p.name.isNotBlank()) Text(p.number,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant) }
                                    val favourite=library.firstOrNull { it.kind=="CONTACT" && it.people.firstOrNull()?.number==p.number }
                                    IconButton(onClick={ scope.launch(Dispatchers.IO) { if(favourite==null) db.save(SavedItem(kind="CONTACT",title=p.name.ifBlank { p.number },people=listOf(p))) else db.deleteSaved(favourite.id) } }) { Icon(if(favourite==null) Icons.Rounded.StarBorder else Icons.Rounded.Star,w.t("Ulubiony","Favourite"),tint=Blue) }
                                }
                            }
                        }
                        Panel(w.t("Karta SIM", "SIM card"),w.t("Nadawcą jest numer wybranej karty SIM.","The sender is the number of your selected SIM card.")) {
                            if(!Sims.permission(context,Manifest.permission.READ_PHONE_STATE)) Button(onClick={requestPermissions()}) { Text(w.t("Włącz dostęp do SMS i SIM","Allow SMS and SIM access")) }
                            else if(sims.isEmpty()) Text(w.t("Brak aktywnych kart SIM. Sprawdź ustawienia telefonu.","No active SIM cards. Check your phone settings."),color=MaterialTheme.colorScheme.error)
                            Box {
                                OutlinedButton(onClick={simMenu=true},enabled=sims.isNotEmpty(),modifier=Modifier.fillMaxWidth()) { Icon(Icons.Rounded.SimCard,null,Modifier.size(20.dp)); Spacer(Modifier.width(8.dp)); Text(selected?.label ?: w.t("Wybierz SIM","Choose SIM")); Icon(Icons.Rounded.ExpandMore,null) }
                                DropdownMenu(expanded=simMenu,onDismissRequest={simMenu=false}) { sims.forEach { s -> DropdownMenuItem(text={Text(s.label)},onClick={selected=s;prefs.selectedSim=s.id;simMenu=false}) } }
                            }
                        }
                        Panel(w.t("Treść SMS", "SMS message")) {
                            OutlinedTextField(value=body,onValueChange={replaceBody(it)},placeholder={Text(w.t("Co chcesz przekazać?","What would you like to say?"))},minLines=5,maxLines=10,modifier=Modifier.fillMaxWidth().testTag("message-body"))
                            val stats=SmsMath.stats(body)
                            val actual=remember(body,selected) { if(body.isEmpty()) 0 else selected?.let { runCatching { Sims.manager(context,it.id).divideMessage(body).size }.getOrNull() } }
                            Text("${stats.encoding} · ${body.length}/1530 · ${actual ?: "~${stats.segments}"} "+w.t("części / odbiorcę","segments / recipient"),style=MaterialTheme.typography.labelMedium,color=Blue)
                            FlowRow(horizontalArrangement=Arrangement.spacedBy(6.dp)) {
                                listOf(w.t("Oddzwonię później.","I'll call you back later."),w.t("Będę za 10 minut.","I'll be there in 10 minutes.")).forEach { sample -> AssistChip(onClick={replaceBody(if(body.isBlank()) sample else "$body\n$sample")},label={Text(sample)}) }
                                AssistChip(onClick={chooseSaved="TEMPLATE"},label={Text(w.t("Moje szablony","My templates"))},leadingIcon={Icon(Icons.Rounded.BookmarkBorder,null,Modifier.size(16.dp))})
                            }
                            Text(w.t("Polskie znaki i emoji mogą zwiększyć liczbę płatnych części. Numer z kodem kraju jest najbezpieczniejszy podczas roamingu.","Accents and emoji may increase billable segments. Use international numbers while roaming."),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                            if(busy) LinearProgressIndicator(Modifier.fillMaxWidth())
                            Button(onClick={review(System.currentTimeMillis())},enabled=!busy,modifier=Modifier.fillMaxWidth().heightIn(min=52.dp).testTag("send-button")) { Icon(Icons.Rounded.Send,null,Modifier.size(20.dp)); Spacer(Modifier.width(8.dp)); Text(w.t("Sprawdź i wyślij","Review and send")) }
                            OutlinedButton(onClick={schedulePicker()},enabled=!busy,modifier=Modifier.fillMaxWidth().testTag("schedule-button")) { Icon(Icons.Rounded.Schedule,null,Modifier.size(18.dp)); Spacer(Modifier.width(8.dp)); Text(w.t("Zaplanuj SMS","Schedule SMS")) }
                            Text(w.t("Harmonogram jest przybliżony: Android może opóźnić wysyłkę. Telefon musi być włączony, mieć zasięg i aktywną SIM.","Scheduling is approximate: Android may delay sending. The phone must be on, have cellular service and an active SIM."),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Text("by Swir",Modifier.align(Alignment.CenterHorizontally),style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    1 -> HistoryScreen(w,history,onCancel={ id -> scope.launch { val cancelled=withContext(Dispatchers.IO) { SmsQueue.cancel(context,id) }; notify(if(cancelled) w.t("Anulowano zaplanowaną wiadomość.","Scheduled message cancelled.") else w.t("Wysyłka już się rozpoczęła — nie można jej cofnąć.","Sending has already started and cannot be recalled.")) } },onLoad={ msg -> replacePeople(listOf(Recipient(msg.name,msg.number)));replaceBody(msg.body);tab=0;notify(w.t("Wczytano do edytora. Nic nie wysłano.","Loaded into the editor. Nothing was sent.")) },onDelete={ id -> scope.launch(Dispatchers.IO) { db.delete(id) } })
                    2 -> LibraryScreen(w,library,people,body,onEdit={edit=it},onUse={ item -> if(item.kind=="TEMPLATE") replaceBody(item.body) else addPeople(item.people);tab=0 },onDelete={ id -> scope.launch(Dispatchers.IO) { db.deleteSaved(id) } })
                    3 -> SettingsScreen(w,lang,reports,lock,permissionRevision,context,onLanguage={lang=it;prefs.lang=it},onReports={reports=it;prefs.reports=it},onLock={ wanted -> activity.authenticate("SwirSMS") { success,msg -> if(success) { lock=wanted;prefs.lock=wanted;activity.updateScreenProtection() } else error=w.detail(msg) } },onPermissions={requestPermissions()},onClear={clearHistory=true})
                }
            }
        }
        error?.let { text -> AlertDialog(onDismissRequest={error=null},title={Text(w.t("Sprawdź przed kontynuacją","Check before continuing"))},text={Text(text)},confirmButton={TextButton(onClick={error=null}) { Text("OK") }}) }
        plan?.let { p ->
            val future=p.due>System.currentTimeMillis()+5_000
            AlertDialog(onDismissRequest={if(!busy) plan=null},title={Text(if(future) w.t("Potwierdź harmonogram","Confirm schedule") else w.t("Potwierdź wysyłkę","Confirm send"))},text={
                Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)) {
                    Text(p.sim.label,fontWeight=FontWeight.Bold)
                    Text("${p.people.size} × ${p.parts} = ${p.people.size*p.parts} "+w.t("części SMS. Obowiązuje taryfa Twojego operatora.","SMS segments. Your carrier's charges apply."))
                    if(future) Text(dateText(p.due)+"\n"+w.t("Android może opóźnić ten termin. Po opóźnieniu >24 h wiadomość wygasa.","Android may delay this time. Messages delayed by >24 h expire."))
                    p.people.forEach { Text(it.name.ifBlank { w.t("Odbiorca","Recipient") }+" · "+it.number,style=MaterialTheme.typography.bodySmall) }
                    HorizontalDivider(); Text(p.body)
                    Text(w.t("Odbiorcy nie widzą innych numerów. Wysłanych SMS-ów nie można cofnąć.","Recipients cannot see the other numbers. Sent SMS cannot be recalled."),style=MaterialTheme.typography.bodySmall)
                }
            },dismissButton={TextButton(onClick={plan=null},enabled=!busy) { Text(w.t("Wróć","Back")) }},confirmButton={Button(enabled=!busy,onClick={
                if(!busy) {
                    busy=true
                    scope.launch {
                        try {
                            withContext(Dispatchers.IO) {
                                val ids=db.addBatch(p.people,p.body,p.sim,p.due,p.reports)
                                ids.forEach { id -> SmsQueue.enqueue(context,id,p.due) }
                            }
                            replaceBody("");plan=null;tab=1
                            notify(w.t("Zapisano w kolejce. Rzeczywiste wyniki pojawią się w historii.","Saved to the queue. Actual results will appear in history."))
                        } catch(e: Exception) { error=w.t("Nie udało się zakończyć operacji. Sprawdź historię przed ponowną próbą, aby nie wysłać podwójnie.","The operation could not be completed. Check history before trying again to avoid duplicates.");plan=null }
                        finally { busy=false }
                    }
                }
            }) { Text(if(future) w.t("Zaplanuj","Schedule") else w.t("Wyślij teraz","Send now")) }})
        }
        chooseSaved?.let { kind ->
            val items=library.filter { it.kind==kind }
            AlertDialog(onDismissRequest={chooseSaved=null},title={Text(w.t("Wybierz z biblioteki","Choose from library"))},text={Column(Modifier.heightIn(max=400.dp).verticalScroll(rememberScrollState())) {
                if(items.isEmpty()) Text(w.t("Jeszcze nic tu nie ma. Dodaj pozycje w zakładce Biblioteka.","Nothing saved yet. Add items in the Library tab."))
                items.forEach { item -> TextButton(onClick={if(kind=="TEMPLATE") replaceBody(item.body) else addPeople(item.people);chooseSaved=null},modifier=Modifier.fillMaxWidth()) { Text(item.title) } }
            }},confirmButton={TextButton(onClick={chooseSaved=null;tab=2}) { Text(w.t("Biblioteka","Library")) }},dismissButton={TextButton(onClick={chooseSaved=null}) { Text(w.t("Zamknij","Close")) }})
        }
        edit?.let { item -> SavedEditor(w,item,onDismiss={edit=null},onSave={ saved -> scope.launch { runCatching { withContext(Dispatchers.IO) { db.save(saved) } }.onSuccess { edit=null }.onFailure { error=w.t("Nie udało się zapisać pozycji.","Could not save item.") } } }) }
        if(clearHistory) AlertDialog(onDismissRequest={clearHistory=false},title={Text(w.t("Wyczyścić historię?","Clear history?"))},text={Text(w.t("Usuniesz zakończone pozycje z tej aplikacji. Kolejka i niepewne wysyłki pozostają. Nie usuwa to SMS-ów z telefonu odbiorcy ani innych aplikacji.","Removes completed entries from this app. Queued and unconfirmed sends remain. This does not remove messages from recipients or other apps."))},confirmButton={TextButton(onClick={scope.launch(Dispatchers.IO) {db.clearFinished()};clearHistory=false}) {Text(w.t("Wyczyść","Clear"))}},dismissButton={TextButton(onClick={clearHistory=false}) {Text(w.t("Anuluj","Cancel"))}})
    }
}
