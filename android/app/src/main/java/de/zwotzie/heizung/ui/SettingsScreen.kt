package de.zwotzie.heizung.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import de.zwotzie.heizung.BuildConfig
import kotlinx.coroutines.launch

/**
 * Einstellungen: Server-Adresse eingeben und prüfen.
 *
 * [onTest] bekommt die eingegebene Adresse und liefert die Zahl der geladenen
 * Zeilen oder einen Fehler.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    current: String?,
    onSave: (String) -> Unit,
    onClose: () -> Unit,
    onTest: suspend (String) -> Result<Int>,
) {
    var text by remember { mutableStateOf(current ?: "https://") }
    var busy by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    val validation = SettingsValidation.messageFor(text)

    Scaffold(
        containerColor = Color.Black,
        topBar = {
            TopAppBar(
                title = { Text("Einstellungen") },
                navigationIcon = {
                    if (current != null) {
                        TextButton(onClick = onClose) { Text("Zurück") }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color.Black,
                    titleContentColor = Color(0xFFDFDFDF),
                ),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier.padding(padding).fillMaxSize().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = "Adresse der Heizungs-API, z. B. https://heizung.example.de",
                fontSize = 12.sp,
                color = Color(0xFF9A9A9A),
            )

            OutlinedTextField(
                value = text,
                onValueChange = {
                    text = it
                    message = null
                },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                isError = validation != null,
                label = { Text("Server-Adresse") },
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Uri,
                    imeAction = ImeAction.Done,
                ),
            )

            if (validation != null) {
                Text(validation, fontSize = 11.sp, color = Color(0xFFF87171))
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Button(
                    onClick = {
                        scope.launch {
                            busy = true
                            message = null
                            val result = onTest(text)
                            message = result.fold(
                                onSuccess = { "$it Zeilen geladen" },
                                onFailure = { it.message ?: "Verbindung fehlgeschlagen" },
                            )
                            busy = false
                        }
                    },
                    enabled = validation == null && !busy,
                ) { Text(if (busy) "Prüfe…" else "Verbindung testen") }

                Button(
                    onClick = { onSave(text) },
                    enabled = validation == null,
                ) { Text("Speichern") }
            }

            message?.let {
                Text(it, fontSize = 12.sp, color = Color(0xFF9A9A9A))
            }

            Text("Version ${BuildConfig.VERSION_NAME}", fontSize = 11.sp, color = Color(0xFF9A9A9A))
        }
    }
}
