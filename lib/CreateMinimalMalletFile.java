import cc.mallet.types.*;
import cc.mallet.pipe.*;
import java.io.*;

public class CreateMinimalMalletFile {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("Usage: java -cp mallet/lib/mallet.jar:mallet/lib/mallet-deps.jar:lib/: CreateMinimalMalletFile <original-instance-list-file> <minimal-instance-list-file>");
            System.exit(1);
        }

        String originalFile = args[0];
        String minimalFile = args[1];

        // Load the original instance list
        InstanceList originalInstances = InstanceList.load(new File(originalFile));
        
        // Create a new instance list with the same pipe
        InstanceList minimalInstances = new InstanceList(originalInstances.getPipe());
        
        // Add just one instance (if available)
        if (originalInstances.size() > 0) {
            minimalInstances.add(originalInstances.get(0));
        }
        
        // Save the minimal instance list
        minimalInstances.save(new File(minimalFile));
    }
}
