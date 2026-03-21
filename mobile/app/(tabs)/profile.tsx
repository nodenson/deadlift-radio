import { StyleSheet, View, Text, Switch } from 'react-native';
import { useState } from 'react';

export default function ProfileScreen() {
  const [isCommand, setIsCommand] = useState(false);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Profile Settings</Text>
      
      <View style={styles.settingRow}>
        <Text style={styles.settingText}>Role: {isCommand ? 'Command' : 'Warrior'}</Text>
        <Switch
          value={isCommand}
          onValueChange={setIsCommand}
          trackColor={{ false: '#3a3a3c', true: '#FF3B30' }}
        />
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
    marginBottom: 24,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1c1c1e',
  },
  settingText: {
    fontSize: 18,
    color: '#fff',
  },
});
