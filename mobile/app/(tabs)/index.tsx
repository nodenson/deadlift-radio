import { StyleSheet, View, Text } from 'react-native';

export default function TodayScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Today's Readiness & Protocol</Text>
      <View style={styles.card}>
        <Text style={styles.cardText}>No protocol assigned yet.</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#000',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 16,
  },
  card: {
    padding: 16,
    borderRadius: 8,
    backgroundColor: '#1c1c1e',
  },
  cardText: {
    color: '#ccc',
  },
});
