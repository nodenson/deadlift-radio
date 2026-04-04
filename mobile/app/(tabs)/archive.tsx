import { useEffect, useState } from "react";
import { StyleSheet, View, Text, FlatList, TouchableOpacity, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { api } from "../../utils/api";

type Session = { id: number; date: string; bodyweight: number | null; notes: string | null };

export default function ArchiveScreen() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    api.getSessions(30).then((data) => {
      setSessions(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>ARCHIVE</Text>
      <Text style={styles.sub}>TRANSMISSION LOG</Text>
      {loading ? (
        <ActivityIndicator color="#555" style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={sessions}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => (
            <TouchableOpacity style={styles.card} onPress={() => router.push(`/modal?id=${item.id}`)}>
              <Text style={styles.date}>{item.date}</Text>
              <Text style={styles.meta}>
                {item.bodyweight ? `${item.bodyweight} lb` : "—"}
                {"  ·  "}
                <Text style={styles.sessionId}>#{item.id}</Text>
              </Text>
            </TouchableOpacity>
          )}
          ItemSeparatorComponent={() => <View style={styles.sep} />}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: "#000" },
  title: { fontSize: 20, fontWeight: "bold", color: "#fff", letterSpacing: 4, marginBottom: 2 },
  sub: { fontSize: 10, color: "#333", letterSpacing: 3, marginBottom: 24 },
  card: { paddingVertical: 14, paddingHorizontal: 4 },
  date: { fontSize: 15, color: "#ccc", letterSpacing: 1 },
  meta: { fontSize: 11, color: "#444", marginTop: 4, letterSpacing: 1 },
  sessionId: { color: "#333" },
  sep: { height: 1, backgroundColor: "#111" },
});
