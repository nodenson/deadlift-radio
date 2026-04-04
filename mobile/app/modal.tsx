import { useEffect, useState } from "react";
import { StyleSheet, View, Text, ScrollView, ActivityIndicator } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { api } from "../utils/api";

export default function ModalScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      api.getSession(Number(id)).then((data) => {
        setSession(data);
        setLoading(false);
      }).catch(() => setLoading(false));
    }
  }, [id]);

  if (loading) return (
    <View style={styles.center}>
      <ActivityIndicator color="#555" />
    </View>
  );

  if (!session) return (
    <View style={styles.center}>
      <Text style={styles.err}>SESSION NOT FOUND</Text>
    </View>
  );

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>SESSION #{session.id}</Text>
      <Text style={styles.sub}>{session.date}  ·  {session.bodyweight ? session.bodyweight + " lb" : "—"}</Text>
      {session.exercises.map((ex: any, i: number) => (
        <View key={i} style={styles.exBlock}>
          <Text style={styles.exName}>{ex.name}</Text>
          <Text style={styles.e1rm}>e1RM {ex.top_e1rm} lb</Text>
          {ex.sets.map((s: any, j: number) => (
            <Text key={j} style={styles.setRow}>{s.load} x {s.reps}</Text>
          ))}
        </View>
      ))}
      <View style={{ height: 60 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000", padding: 20 },
  center: { flex: 1, backgroundColor: "#000", alignItems: "center", justifyContent: "center" },
  title: { fontSize: 18, color: "#fff", fontWeight: "bold", letterSpacing: 4, marginBottom: 4 },
  sub: { fontSize: 11, color: "#444", letterSpacing: 2, marginBottom: 28 },
  exBlock: { marginBottom: 24 },
  exName: { fontSize: 13, color: "#ccc", letterSpacing: 1, marginBottom: 4 },
  e1rm: { fontSize: 10, color: "#444", letterSpacing: 2, marginBottom: 6 },
  setRow: { fontSize: 13, color: "#555", paddingVertical: 2 },
  err: { color: "#333", letterSpacing: 3, fontSize: 12 },
});
