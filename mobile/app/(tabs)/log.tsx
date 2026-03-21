import { StyleSheet, View, Text, TextInput, TouchableOpacity } from 'react-native';

export default function LogScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Log Session</Text>
      
      <View style={styles.inputContainer}>
        <Text style={styles.label}>Exercise</Text>
        <TextInput style={styles.input} placeholder="e.g. Squat" placeholderTextColor="#666" />
      </View>

      <View style={styles.row}>
        <View style={[styles.inputContainer, { flex: 1, marginRight: 8 }]}>
          <Text style={styles.label}>Load (lbs)</Text>
          <TextInput style={styles.input} placeholder="0" keyboardType="numeric" placeholderTextColor="#666" />
        </View>
        <View style={[styles.inputContainer, { flex: 1 }]}>
          <Text style={styles.label}>Reps</Text>
          <TextInput style={styles.input} placeholder="0" keyboardType="numeric" placeholderTextColor="#666" />
        </View>
      </View>

      <TouchableOpacity style={styles.button}>
        <Text style={styles.buttonText}>Log Set</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#000' },
  title: { fontSize: 24, fontWeight: 'bold', color: '#fff', marginBottom: 16 },
  inputContainer: { marginBottom: 16 },
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  label: { color: '#aaa', marginBottom: 4 },
  input: { backgroundColor: '#1c1c1e', color: '#fff', padding: 12, borderRadius: 8 },
  button: { backgroundColor: '#FF3B30', padding: 16, borderRadius: 8, alignItems: 'center', marginTop: 16 },
  buttonText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
});
