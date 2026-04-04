import { useState } from "react";
import { StyleSheet, View, Text, TextInput, TouchableOpacity, ScrollView, Alert } from "react-native";
import { api } from "../../utils/api";

export default function LogScreen() {
  const [rawText, setRawText] = useState("");
  const [saving, setSaving] = useState(false);

  async function save() {
    if (!rawText.trim()) { Alert.alert("Empty log", "Paste your workout first."); return; }
    setSaving(true);
    try {
      const result = await api.logRaw(rawText.trim());
      Alert.alert("TRANSMITTED", "Session #" + result.id + " recorded.");
      setRawText("");
    } catch (e) {
      Alert.alert("FAILED", "Could not save session. Check API connection.");
    }
    setSaving(false);
  }

  return (
    <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
      <Text style={styles.title}>LOG SESSION</Text>
      <Text style={styles.sub}>PASTE RAW TRANSMISSION</Text>
      <TextInput
        style={styles.input}
        value={rawText}
        onChangeText={setRawText}
        multiline
        placeholder={"March 27th, 2026\n\nBench Press\n135 x 10\n225 x 5\n\nTriceps Pushdown\n100 x 12"}
        placeholderTextColor="#222"
        textAlignVertical="top"
      />
      <TouchableOpacity onPress={save} style={styles.saveBtn} disabled={saving}>
        <Text style={styles.saveTxt}>{saving ? "TRANSMITTING..." : "COMMIT SESSION"}</Text>
      </TouchableOpacity>
      <View style={{ height: 60 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000", padding: 20 },
  title: { fontSize: 20, color: "#fff", fontWeight: "bold", letterSpacing: 4, marginBottom: 2 },
  sub: { fontSize: 10, color: "#333", letterSpacing: 3, marginBottom: 24 },
  input: { backgroundColor: "#0f0f0f", color: "#ccc", padding: 16, borderRadius: 4, fontSize: 13, borderWidth: 1, borderColor: "#1a1a1a", minHeight: 300, marginBottom: 16 },
  saveBtn: { backgroundColor: "#fff", borderRadius: 4, padding: 16, alignItems: "center" },
  saveTxt: { color: "#000", fontSize: 12, fontWeight: "bold", letterSpacing: 4 },
});
