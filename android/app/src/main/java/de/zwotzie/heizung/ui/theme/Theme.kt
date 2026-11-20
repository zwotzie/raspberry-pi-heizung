package de.zwotzie.heizung.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val HeizungColors = darkColorScheme(
    primary = Color(0xFF6EA8FE),
    onPrimary = Color(0xFF04121F),
    background = Color(0xFF000000),
    onBackground = Color(0xFFDFDFDF),
    surface = Color(0xFF0C0C0C),
    onSurface = Color(0xFFDFDFDF),
    surfaceVariant = Color(0xFF1C1C1C),
    onSurfaceVariant = Color(0xFFBBBBBB),
    outline = Color(0xFF333333),
)

/** Durchgehend dunkles Schema, passend zur Weboberfläche. */
@Composable
fun HeizungTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = HeizungColors, content = content)
}
